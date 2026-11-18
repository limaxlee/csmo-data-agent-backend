import { NextResponse } from "next/server"
import { readDevLoginConfig } from "../config"

export const dynamic = "force-dynamic"

export async function GET() {
  const config = readDevLoginConfig()
  return NextResponse.json(
    { enabled: config.enabled, allowAdmin: config.enabled && config.allowAdmin },
    { headers: { "Cache-Control": "no-store" } },
  )
}
