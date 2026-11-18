import { NextRequest, NextResponse } from "next/server"
import { isNextResponse, requireReleaseRole } from "../../lib/releaseAuth"
import { getBucket, headObject } from "../../lib/releaseS3"

const PREFIXES = {
  internal: process.env.RUNNER_DOCS_INTERNAL_STORAGE_PREFIX || "runner-docs/internal",
  partner: process.env.RUNNER_DOCS_PARTNER_STORAGE_PREFIX || "runner-docs/partner",
} as const

export async function GET(request: NextRequest) {
  const auth = await requireReleaseRole(request)
  if (isNextResponse(auth)) return auth

  const bucket = getBucket()
  const assets = []
  for (const audience of ["internal", "partner"] as const) {
    const prefix = PREFIXES[audience].replace(/^\/+|\/+$/g, "")
    for (const lang of ["ko", "en"] as const) {
      const fileName = `runner-manual-${audience}-${lang}.html`
      const head = await headObject(bucket, `${prefix}/latest/${fileName}`)
      if (!head) continue
      assets.push({
        audience,
        lang,
        file_name: fileName,
        size_bytes: Number(head.ContentLength ?? 0),
        updated_at: head.LastModified?.toISOString() ?? null,
      })
    }
  }

  return NextResponse.json({ assets }, { headers: { "Cache-Control": "no-store" } })
}
