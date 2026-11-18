import { ListObjectsV2Command } from "@aws-sdk/client-s3"
import { NextRequest, NextResponse } from "next/server"
import { isNextResponse, requireReleaseRole } from "../lib/releaseAuth"
import { getBucket, getS3Client, headObject, loadJsonObject } from "../lib/releaseS3"
import { storagePrefix } from "./prefix"

function aliasFromKey(storageKey: string): string {
  const fileName = storageKey.split("/").pop() || storageKey
  const name = fileName.toLowerCase().endsWith(".zip") ? fileName.slice(0, -4) : fileName
  const stripPrefixes = [
    "dice-env-linux-x86_64-",
    "dice-env-windows-x86_64-",
    "dice-env-linux-",
    "dice-env-windows-",
    "env-",
  ]
  for (const prefix of stripPrefixes) {
    if (name.startsWith(prefix)) return name.slice(prefix.length)
  }
  return name
}

function assetId(storageKey: string): string {
  return Buffer.from(storageKey, "utf-8").toString("base64url")
}

function iterManifestAssets(manifest: any): Array<{ entry: any; storageKey: string }> {
  const assets = Array.isArray(manifest?.assets) ? manifest.assets : Array.isArray(manifest?.envs) ? manifest.envs : null
  if (assets) {
    return assets
      .filter((entry: any) => entry && typeof entry === "object")
      .map((entry: any) => ({ entry, storageKey: String(entry.storage_key || entry.key || "").trim() }))
      .filter((item: any) => item.storageKey)
  }
  const singleKey = manifest?.storage_key || manifest?.key
  if (typeof singleKey === "string" && singleKey.trim()) {
    return [{ entry: manifest, storageKey: singleKey.trim() }]
  }
  return []
}

async function listZipObjects(bucket: string, prefix: string) {
  const objects: { Key?: string; LastModified?: Date; Size?: number }[] = []
  let token: string | undefined
  do {
    const response = await getS3Client().send(
      new ListObjectsV2Command({ Bucket: bucket, Prefix: `${prefix}/`, ContinuationToken: token }),
    )
    for (const obj of response.Contents || []) {
      if (obj.Key?.toLowerCase().endsWith(".zip")) objects.push(obj)
    }
    token = response.IsTruncated ? response.NextContinuationToken : undefined
  } while (token)
  return objects
}

export async function GET(request: NextRequest) {
  const auth = await requireReleaseRole(request)
  if (isNextResponse(auth)) return auth

  const { searchParams } = new URL(request.url)
  let prefix: string
  try {
    prefix = storagePrefix(searchParams.get("platform"))
  } catch (error) {
    return NextResponse.json({ detail: (error as Error).message }, { status: 400 })
  }

  const bucket = getBucket()
  let manifest = await loadJsonObject(bucket, `${prefix}/manifest.json`)
  if (manifest === null) manifest = await loadJsonObject(bucket, `${prefix}/latest/manifest.json`)

  let candidates = iterManifestAssets(manifest)
  if (candidates.length === 0) {
    candidates = (await listZipObjects(bucket, prefix)).map((obj) => ({ entry: {}, storageKey: String(obj.Key) }))
  }

  const assets = []
  for (const { entry, storageKey } of candidates) {
    if (!(storageKey === prefix || storageKey.startsWith(`${prefix}/`)) || !storageKey.toLowerCase().endsWith(".zip")) {
      continue
    }
    const head = await headObject(bucket, storageKey)
    if (!head) continue

    const fileName = String(entry.file_name || head.Metadata?.file_name || storageKey.split("/").pop())
    assets.push({
      id: assetId(storageKey),
      alias: String(entry.alias || entry.env_alias || head.Metadata?.alias || aliasFromKey(storageKey)).trim(),
      version: String(entry.version || head.Metadata?.version || ""),
      file_name: fileName,
      storage_key: storageKey,
      size_bytes: Number(head.ContentLength ?? entry.size_bytes ?? 0),
      sha256: String(entry.sha256 || head.Metadata?.sha256 || "").toLowerCase(),
      updated_at: (head.LastModified || new Date()).toISOString(),
      platform: String(entry.platform || head.Metadata?.platform || "linux"),
      arch: String(entry.arch || head.Metadata?.arch || "x86_64"),
      cuda: entry.cuda || head.Metadata?.cuda ? String(entry.cuda || head.Metadata?.cuda).trim() || null : null,
      frameworks: Array.isArray(entry.frameworks) ? entry.frameworks : [],
      description: String(entry.description || head.Metadata?.description || ""),
    })
  }
  assets.sort((a, b) => (a.alias + a.version + a.file_name).localeCompare(b.alias + b.version + b.file_name))

  return NextResponse.json(
    { bucket, prefix, assets },
    { headers: { "Cache-Control": "no-store" } },
  )
}
