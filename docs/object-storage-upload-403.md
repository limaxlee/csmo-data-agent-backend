# Object storage uploads refused with `403 Forbidden`

**Repository:** `limaxlee/csmo-data-agent-backend`
**Audience:** maintainers, and whoever owns the proxy or gateway in front of the object storage
**Status:** open — cause narrowed to the network path, fix pending the probe output
**Component:** [object_storage.py](../data_agent/infra/object_storage.py), probe in [check_upload.py](../temp/check_upload.py)
**Related:** [architecture.en.md](architecture.en.md)

## TL;DR

Artifact uploads fail with

```
Failed to upload object data_agent/243952000_20250618025416_AA3_EPOXY_AI.bmp/0 to bucket cosmo-storage-stage:
An error occurred (403) when calling the PutObject operation: Forbidden
```

The upload code has not changed and used to work. The same credentials work from another
application. Small uploads still succeed and only larger ones fail, each refused within a few
milliseconds and with no response body. Those three facts together say the request is being
refused **before it reaches the S3 backend**, on its `Content-Length`, by a proxy, gateway or WAF
rule. The service runs with `HTTP_PROXY` and `HTTPS_PROXY` set, so the forward proxy is the
first suspect. It is not a credentials or bucket-policy problem.

## 1. What was observed

Uploading zero-filled payloads of growing size with the app's own `ObjectStorage.upload_object`:

| Size | Result |
|---|---|
| 10,000 bytes | uploaded |
| 100,000 bytes | `403 Forbidden`, empty body, empty request id |
| 500,000 bytes and up | same |

Every failure came back in roughly 25 ms. Listing, `head_bucket` and small `PutObject` calls work.

## 2. Reading the error message

botocore builds `An error occurred (<Code>) ... : <Message>` from the XML error body the S3
service returns. A genuine S3 refusal therefore reads `(AccessDenied) ... Access Denied` and
carries an `x-amz-request-id`. When the response has **no parseable body**, botocore falls back
to the HTTP status and reason phrase, which is exactly the `(403) ... Forbidden` seen here, with
`RequestId` empty. That fallback was reproduced locally by faking a bodyless 403.

Conclusion: the reply did not come from the S3 service, or at least not from its request
handling. Something in front of it answered.

## 3. Why the size matters

A 25 ms refusal on a 100 KB body cannot be the result of inspecting the body: the client had
barely started sending it. The deciding input is the `Content-Length` header. Components that
behave this way:

- **Forward proxies** with upload or DLP policies (they pass small requests and block large ones
  with a bare 403).
- **WAFs** with a body-inspection limit and "oversize handling = block" (limits of 8, 16, 32 or
  64 KB are common; anything larger is rejected with a bodyless 403).
- **Gateways / reverse proxies** with a `client_max_body_size` style rule (these usually answer
  413, but some are configured to answer 403).

Because nothing in this repository changed, the rule was added or tightened on one of those
components, or the proxy environment of this deployment changed.

## 4. How the proxy is involved

botocore reads `HTTP_PROXY`, `HTTPS_PROXY` and `NO_PROXY` from the environment, and aiobotocore
sends every request through the proxy named there. With `HTTPS_PROXY` set, every call to
`https://gage.ap-northeast-2.samsungspc.com` goes through that proxy unless the host is listed in
`NO_PROXY`. An application that runs without those variables, or with the storage host excluded,
talks to the storage directly and never meets the proxy's rules. That is the most likely
difference between this service and the application where uploads work.

Quick check, in the environment where the service runs:

```
env | grep -i proxy
# Then, bypassing the proxy for one process:
NO_PROXY=gage.ap-northeast-2.samsungspc.com python temp/check_upload.py -c /path/config.yaml
```

If the sweep passes with `NO_PROXY` set and fails without it, the proxy is the cause.

## 5. What the client sends

Captured offline by intercepting the request the app's client builds for the failing key:

```
PUT https://gage.ap-northeast-2.samsungspc.com/cosmo-storage-stage/data_agent/<...>.bmp/0
Authorization: AWS4-HMAC-SHA256 Credential=<key>/<date>/us-east-1/s3/aws4_request, ...
Content-Type: image/bmp
Content-MD5: <md5>
Expect: 100-continue
X-Amz-Content-SHA256: UNSIGNED-PAYLOAD
```

Points worth knowing when comparing with another SDK setup:

- The signing region is `us-east-1` because no `region_name` is configured; botocore defaults
  S3 to that region. The endpoint itself is in `ap-northeast-2`. Most S3-compatible stores ignore
  the scope region, but a strict one would refuse every call, not only large ones.
- Path-style addressing is used (bucket in the path, not the hostname).
- Pinned `botocore==1.35.93` predates the 1.36 default checksum headers that broke many
  S3-compatible stores, so that known breakage does not apply here.

None of these vary with payload size, which is why they are not the primary suspects. They are
still exercised by the probe's variant phase so the comparison with the working app is complete.

## 6. The probe: `temp/check_upload.py`

Run it where the service runs, with the same config the service uses:

```
python temp/check_upload.py -c /home/work/cosmo-da-backend/config.yaml
python temp/check_upload.py -c /path/config.yaml --debug      # full botocore wire logs
python temp/check_upload.py -c /path/config.yaml --variants   # force phase 2 even if all passes
```

It prints the endpoint, bucket and every proxy variable, then runs three phases. Probe objects
live under `data_agent/check_upload/` and `check_upload/` and are deleted after each step.

**Phase 0 — size sweep.** Uploads 10 KB, 16 KB, 20 KB, 32 KB, 50 KB, 64 KB, 70 KB and 100 KB
with the app's own client and reports the smallest failing size. The sizes bracket the common
WAF and proxy inspection limits.

**Phase 1 — the app's client.** `head_bucket`, list, upload, get and delete, once under the
`data_agent/` prefix and once outside it, to separate a prefix policy from a global block.

**Phase 2 — client variants.** Repeats `PutObject` with one setting changed at a time: region
`ap-northeast-2`, path vs virtual addressing, signed payload, SigV2, no `Expect` header, no
`Content-MD5`. A summary table shows which variants succeed.

Every failed call prints the **raw HTTP response**: status, all headers and the body. This is
the part that answers the question. Read it as follows:

| Raw reply | Meaning |
|---|---|
| `Server`, `Via` or `X-Cache` header naming a proxy or gateway product, empty body | refused by that component, not by S3 |
| XML body with `<Code>AccessDenied</Code>` and an `x-amz-request-id` | genuine S3 denial: credentials or bucket policy |
| XML body with `<Code>EntityTooLarge</Code>` or status 413 | size limit on the storage side |
| Phase 0 fails but passes with `NO_PROXY` set | forward proxy rule |

## 7. Fix by cause

| Cause | Fix |
|---|---|
| Forward proxy blocks large uploads | Add the storage host to `NO_PROXY` for this service (container env or `run_data_agent_backend.sh`), or run it on the same network path as the working app |
| WAF or gateway body limit | The owner raises the limit for this bucket or client; until then, upload large artifacts with multipart parts below the limit |
| Storage-side size limit (`EntityTooLarge`) | Switch `upload_object` to multipart for large payloads |
| Genuine `AccessDenied` on the `data_agent/` prefix only | Extend the bucket policy to that prefix |
| A variant in phase 2 passes while the baseline fails | Set that option in the client `Config` in `ObjectStorage.connect` |

## 8. Ruled out

- Credentials and bucket policy: a policy denial produces `AccessDenied` with a request id and
  does not depend on payload size.
- The object key format (`<app>/<user>/<session>/<filename>/<version>`): the 10 KB upload used
  the same shape and succeeded.
- botocore 1.36 checksum headers: not present in the pinned version.
- Code regression: the upload path in `object_storage.py` is unchanged since uploads worked.
