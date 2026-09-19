"""Exercise only ObjectStorage with the app config. Run from the repo root:

    python temp/check_upload.py                       # uses ./config.yaml
    python temp/check_upload.py -c /path/config.yaml  # inside the container

Each step prints OK or the full traceback of the failing call.
"""
import asyncio
import logging
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

from common.config import SETTINGS  # noqa: E402
from data_agent.infra.object_storage import ObjectStorage  # noqa: E402

KEY = "check_upload/probe.txt"


async def step(name, coro):
    print(f"\n--- {name} ---")
    try:
        result = await coro
        print(f"OK: {result!r}")
        return result
    except Exception:
        traceback.print_exc()
        return None


async def main():
    print("endpoint :", SETTINGS.object_storage.endpoint)
    print("bucket   :", SETTINGS.object_storage.bucket)
    print("proxy env:", {k: v for k, v in os.environ.items() if "proxy" in k.lower()} or "none")

    storage = ObjectStorage()
    await step("connect (builds the client, no network)", storage.connect())
    await step("head_bucket (first real network call)", storage.client.head_bucket(Bucket=storage.bucket))
    await step("list_paginated_objects", storage.list_paginated_objects(prefix="check_upload/", max_items=5))
    await step("upload_object (put_object)", storage.upload_object(b"probe", key=KEY, content_type="text/plain"))
    await step("retrieve_object", storage.retrieve_object(key=KEY))
    await step("delete_objects", storage.delete_objects(keys=[KEY]))
    await storage.close()


if __name__ == "__main__":
    asyncio.run(main())
