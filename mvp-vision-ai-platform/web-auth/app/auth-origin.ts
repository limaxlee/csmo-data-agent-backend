import { NextRequest, NextResponse } from "next/server"

function normalizeOrigin(value: string): string | null {
  const raw = value.trim().replace(/\/+$/, "")
  if (!raw) return null

  try {
    return new URL(raw).origin
  } catch {
    return raw
  }
}

export function allowedCallbackOrigins(): string[] {
  return (process.env.AUTH_ALLOWED_CALLBACK_ORIGINS || "")
    .split(",")
    .map((value) => normalizeOrigin(value))
    .filter((value): value is string => Boolean(value))
}

export function isAllowedCallbackOrigin(origin: string): boolean {
  const normalized = normalizeOrigin(origin)
  if (!normalized) return false
  return allowedCallbackOrigins().includes(normalized)
}

function corsHeaders(request: NextRequest, methods: string): Record<string, string> {
  const origin = request.headers.get("origin")
  if (!origin || !isAllowedCallbackOrigin(origin)) {
    return {}
  }

  return {
    "Access-Control-Allow-Origin": origin,
    "Access-Control-Allow-Credentials": "true",
    "Access-Control-Allow-Methods": methods,
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Vary": "Origin",
  }
}

export function withCors(request: NextRequest, response: NextResponse, methods = "GET, OPTIONS"): NextResponse {
  Object.entries(corsHeaders(request, methods)).forEach(([key, value]) => {
    response.headers.set(key, value)
  })
  return response
}

export function corsPreflight(request: NextRequest, methods = "GET, OPTIONS"): NextResponse {
  const response = new NextResponse(null, { status: 204 })
  response.headers.set("Access-Control-Max-Age", "600")
  return withCors(request, response, methods)
}

