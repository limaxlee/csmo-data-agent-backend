import { NextResponse } from "next/server"

// Validates a client-supplied storage_key against the resolved runner-envs
// prefix before it's ever handed to presignGetUrl. Segment-checked for "."/".."
// separately from the prefix check: a traversal payload like
// "runner-envs/linux/../../secrets/x.zip" still textually startsWith the
// prefix (S3 keys aren't resolved like filesystem paths), so the prefix check
// alone wouldn't catch it.
export function normalizeStorageKey(storageKey: string, prefix: string): string | NextResponse {
  const key = (storageKey || "").trim().replace(/^\/+/, "")
  if (!key) return NextResponse.json({ detail: "storage_key is required" }, { status: 400 })
  if (key.endsWith("/")) {
    return NextResponse.json({ detail: "storage_key must be an object" }, { status: 400 })
  }
  if (key.split("/").some((segment) => segment === "." || segment === "..")) {
    return NextResponse.json({ detail: "storage_key must not contain '.' or '..' segments" }, { status: 400 })
  }
  if (!(key === prefix || key.startsWith(`${prefix}/`))) {
    return NextResponse.json({ detail: `storage_key must be under '${prefix}/'` }, { status: 400 })
  }
  if (!key.toLowerCase().endsWith(".zip")) {
    return NextResponse.json({ detail: "storage_key must point to a .zip env bundle" }, { status: 400 })
  }
  return key
}

