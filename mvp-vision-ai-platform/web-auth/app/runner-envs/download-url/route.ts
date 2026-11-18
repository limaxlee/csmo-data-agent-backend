import { NextRequest, NextResponse } from "next/server"
import { isNextResponse, requireReleaseRole } from "../../lib/releaseAuth"
import { clampExpiresIn, getBucket, headObject, presignGetUrl } from "../../lib/releaseS3"
import { storagePrefix } from "../prefix"
import { normalizeStorageKey } from "../storageKey"

const DEFAULT_EXPIRES_IN = Number(process.env.RUNNER_ENV_PRESIGN_EXPIRE_SECONDS || 3600)

export async function POST(request: NextRequest) {
  const auth = await requireReleaseRole(request)
  if (isNextResponse(auth)) return auth

  const { searchParams } = new URL(request.url)
  let prefix: string
  try {
    prefix = storagePrefix(searchParams.get("platform"))
  } catch (error) {
    return NextResponse.json({ detail: (error as Error).message }, { status: 400 })
  }

  let body: any
  try {
    body = await request.json()
  } catch {
    return NextResponse.json({ detail: "Invalid JSON body" }, { status: 400 })
  }

  const key = normalizeStorageKey(String(body?.storage_key || ""), prefix)
  if (key instanceof NextResponse) return key

  const bucket = getBucket()
  if (!(await headObject(bucket, key))) {
    return NextResponse.json({ detail: "Runner env bundle not found" }, { status: 404 })
  }

  const expiresIn = clampExpiresIn(body?.expiration_seconds, DEFAULT_EXPIRES_IN)
  const downloadUrl = await presignGetUrl(bucket, key, expiresIn)

  return NextResponse.json(
    { storage_key: key, download_url: downloadUrl, expires_in: expiresIn },
    { headers: { "Cache-Control": "no-store" } },
  )
}
