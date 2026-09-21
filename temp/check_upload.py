"""Exercise ObjectStorage with the app config and find out why PutObject is refused.

    python temp/check_upload.py                       # uses ./config.yaml
    python temp/check_upload.py -c /path/config.yaml  # inside the container
    python temp/check_upload.py --debug               # full botocore wire logs

Phase 0 uploads growing payloads to locate the size threshold.
Phase 1 runs the app's own client (head_bucket, list, put, get, delete) and
dumps the raw HTTP response of every failed call: status, headers and body.
The headers tell you which server refused the request (S3 backend vs. a
gateway, WAF or proxy) and the body carries the real S3 error code when there
is one. Phase 2 retries PutObject with client variants that commonly differ
between S3 SDK setups so you can see which one your other app relies on.
"""
import argparse
import asyncio
import logging
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

from aiobotocore.session import get_session  # noqa: E402
from botocore.config import Config  # noqa: E402

from common.config import SETTINGS  # noqa: E402
from data_agent.infra.object_storage import ObjectStorage  # noqa: E402

PROBE_KEYS = [
    "data_agent/check_upload/probe.bmp/0",   # same shape as the failing key
    "check_upload/probe.txt",                # outside the data_agent/ prefix
]
# Sizes for the sweep: 10 KB is known to pass and 100 KB to fail, so the
# threshold is between; 16 KB / 32 KB / 64 KB are common WAF and proxy
# body-inspection limits (a bodyless 403 within milliseconds means the
# request was refused on its Content-Length before the body was read).
SWEEP_SIZES = (10_000, 16_384, 20_000, 32_768, 50_000, 65_536, 70_000, 100_000)


async def dump_failed_response(http_response=None, parsed=None, **_):
    """after-call hook: print the raw response of any non-2xx reply."""
    if http_response is None or http_response.status_code < 300:
        return
    print(f"    raw status : {http_response.status_code}")
    for name, value in http_response.headers.items():
        print(f"    raw header : {name}: {value}")
    try:
        body = await http_response.content
    except Exception as e:  # noqa: BLE001
        body = f"<unreadable: {e}>"
    print(f"    raw body   : {body[:2000]!r}")
    print(f"    parsed err : {parsed.get('Error') if isinstance(parsed, dict) else parsed}")


def hook(client):
    client.meta.events.register("after-call.s3", dump_failed_response)


async def step(name, coro):
    print(f"\n--- {name} ---")
    try:
        result = await coro
        print(f"OK: {result!r}")
        return result
    except Exception:
        traceback.print_exc()
        return None


async def phase_0(storage):
    """Upload growing payloads and print the raw reply of the first failures."""
    print("\n=== Phase 0: size sweep with the app's client ===")
    await storage.connect()
    hook(storage.client)
    import time
    first_fail = None
    for size in SWEEP_SIZES:
        key = f"data_agent/check_upload/size_{size}.bin"
        print(f"\n--- PUT {size} bytes ---")
        started = time.perf_counter()
        ok = await storage.upload_object(b"\x00" * size, key=key)
        print(f"{'OK' if ok else 'FAIL'} after {time.perf_counter() - started:.3f}s")
        if ok:
            await storage.delete_objects(keys=[key])
        elif first_fail is None:
            first_fail = size
    print(f"\nsmallest failing size: {first_fail}")
    return first_fail


async def phase_1(storage):
    print("\n=== Phase 1: the app's own client ===")
    await step("connect (builds the client, no network)", storage.connect())
    hook(storage.client)
    print("signing region:", storage.client.meta.region_name)
    await step("head_bucket", storage.client.head_bucket(Bucket=storage.bucket))
    await step("list_paginated_objects", storage.list_paginated_objects(prefix="check_upload/", max_items=5))
    results = {}
    for key in PROBE_KEYS:
        results[key] = await step(f"upload_object {key}", storage.upload_object(b"probe", key=key, content_type="image/bmp"))
        if results[key]:
            await step(f"retrieve_object {key}", storage.retrieve_object(key=key))
            await step(f"delete_objects {key}", storage.delete_objects(keys=[key]))
    return results


def _drop_header(name):
    async def handler(request, **_):
        request.headers.pop(name, None)
    return handler


VARIANTS = {
    "baseline (as the app: no region, s3v4, auto addressing)": dict(config=Config(signature_version="s3v4")),
    "region=ap-northeast-2": dict(region_name="ap-northeast-2", config=Config(signature_version="s3v4")),
    "addressing_style=path": dict(config=Config(signature_version="s3v4", s3={"addressing_style": "path"})),
    "addressing_style=virtual": dict(config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"})),
    "region=ap-northeast-2 + path": dict(region_name="ap-northeast-2", config=Config(signature_version="s3v4", s3={"addressing_style": "path"})),
    "signed payload (x-amz-content-sha256 = real hash)": dict(config=Config(signature_version="s3v4", s3={"payload_signing_enabled": True})),
    "signature_version=s3 (SigV2)": dict(config=Config(signature_version="s3")),
    "no 'Expect: 100-continue' header": dict(config=Config(signature_version="s3v4"), drop_header="Expect"),
    "no Content-MD5 header": dict(config=Config(signature_version="s3v4"), drop_header="Content-MD5"),
}


async def phase_2(bucket, key):
    print("\n=== Phase 2: PutObject with client variants ===")
    cfg = SETTINGS.object_storage
    session = get_session()
    outcome = {}
    for label, opts in VARIANTS.items():
        drop = opts.pop("drop_header", None)
        print(f"\n--- {label} ---")
        try:
            async with session.create_client(
                "s3",
                endpoint_url=cfg.endpoint,
                aws_access_key_id=cfg.access_key,
                aws_secret_access_key=cfg.secret_key,
                **opts,
            ) as client:
                hook(client)
                if drop:
                    client.meta.events.register("before-sign.s3.PutObject", _drop_header(drop))
                await client.put_object(Bucket=bucket, Key=key, Body=b"probe", ContentType="image/bmp")
                print("OK")
                outcome[label] = "OK"
                try:
                    await client.delete_object(Bucket=bucket, Key=key)
                except Exception as e:  # noqa: BLE001
                    print(f"(cleanup delete failed: {e})")
        except Exception as e:  # noqa: BLE001
            print(f"FAIL: {e}")
            outcome[label] = f"FAIL: {e}"
    return outcome


async def main(args):
    print("endpoint :", SETTINGS.object_storage.endpoint)
    print("bucket   :", SETTINGS.object_storage.bucket)
    print("proxy env:", {k: v for k, v in os.environ.items() if "proxy" in k.lower()} or "none")

    storage = ObjectStorage()
    threshold = await phase_0(storage)
    results = await phase_1(storage)
    await storage.close()
    if threshold:
        print(f"\nUploads above ~{threshold} bytes are refused; small ones pass. Look at the raw "
              "headers above: the 'Server'/'Via'/'X-Cache' style headers and an empty body identify "
              "a gateway, WAF or proxy rather than the S3 backend.")

    if all(results.values()) and not args.variants:
        print("\nAll uploads succeeded with the app's client; nothing to compare.")
        return

    outcome = await phase_2(SETTINGS.object_storage.bucket, PROBE_KEYS[0])
    print("\n=== Summary ===")
    for label, result in outcome.items():
        print(f"  {result[:80]:<80}  <- {label}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--debug", action="store_true", help="botocore/aiobotocore wire-level logs")
    parser.add_argument("--variants", action="store_true", help="run phase 2 even if phase 1 passed")
    known, _ = parser.parse_known_args()  # leave -c for common.config
    if known.debug:
        logging.getLogger("botocore").setLevel(logging.DEBUG)
        logging.getLogger("aiobotocore").setLevel(logging.DEBUG)
    asyncio.run(main(known))
