import { describe, expect, it } from "vitest"
import { NextResponse } from "next/server"
import { normalizeStorageKey } from "./storageKey"

const PREFIX = "runner-envs/linux"

async function detailOf(result: string | NextResponse): Promise<string> {
  if (!(result instanceof NextResponse)) throw new Error("expected a NextResponse")
  const body = await result.json()
  return body.detail as string
}

describe("normalizeStorageKey", () => {
  it("accepts a valid key under the prefix", () => {
    const result = normalizeStorageKey("runner-envs/linux/torch/1/env.zip", PREFIX)
    expect(result).toBe("runner-envs/linux/torch/1/env.zip")
  })

  it("strips a leading slash", () => {
    const result = normalizeStorageKey("/runner-envs/linux/env.zip", PREFIX)
    expect(result).toBe("runner-envs/linux/env.zip")
  })

  it("rejects an empty key", async () => {
    const result = normalizeStorageKey("", PREFIX)
    expect(result).toBeInstanceOf(NextResponse)
    expect((result as NextResponse).status).toBe(400)
  })

  it("rejects a key ending in a trailing slash", async () => {
    const result = normalizeStorageKey("runner-envs/linux/dir/", PREFIX)
    expect((result as NextResponse).status).toBe(400)
  })

  it("rejects a key containing a '..' segment (path traversal)", async () => {
    const result = normalizeStorageKey("runner-envs/linux/../../secrets/leak.zip", PREFIX)
    expect(result).toBeInstanceOf(NextResponse)
    expect((result as NextResponse).status).toBe(400)
    expect(await detailOf(result)).toMatch(/\.\./)
  })

  it("rejects a key containing a '.' segment", async () => {
    const result = normalizeStorageKey("runner-envs/linux/./env.zip", PREFIX)
    expect((result as NextResponse).status).toBe(400)
  })

  it("rejects a key outside the configured prefix", async () => {
    const result = normalizeStorageKey("some-other-prefix/env.zip", PREFIX)
    expect((result as NextResponse).status).toBe(400)
    expect(await detailOf(result)).toMatch(/must be under/)
  })

  it("rejects a non-.zip key", async () => {
    const result = normalizeStorageKey("runner-envs/linux/env.txt", PREFIX)
    expect((result as NextResponse).status).toBe(400)
    expect(await detailOf(result)).toMatch(/\.zip/)
  })
})
