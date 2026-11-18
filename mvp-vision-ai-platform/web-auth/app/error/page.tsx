"use client"

import { Suspense } from "react"
import { signIn } from "next-auth/react"
import { useSearchParams } from "next/navigation"

const messages: Record<string, string> = {
  Configuration: "The authentication server is not configured correctly.",
  AccessDenied: "Access was denied.",
  Verification: "The verification step failed.",
  OAuthSignin: "The login flow could not be started.",
  OAuthCallback: "The identity provider callback failed.",
  SessionRequired: "A login session is required.",
  Default: "Authentication failed.",
}

function ErrorContent() {
  const searchParams = useSearchParams()
  const error = searchParams?.get("error") || "Default"
  const message = messages[error] || messages.Default

  return (
    <section style={{ maxWidth: 440, border: "1px solid #fecaca", borderRadius: 8, background: "#fff", padding: 28, textAlign: "center" }}>
      <p style={{ color: "#dc2626", fontWeight: 900, margin: "0 0 8px" }}>Authentication Error</p>
      <h1 style={{ fontSize: 24, margin: "0 0 12px" }}>Login failed</h1>
      <p style={{ color: "#475569", lineHeight: 1.6 }}>{message}</p>
      <p style={{ color: "#94a3b8", fontSize: 12 }}>Error code: {error}</p>
      <button
         => signIn("adfs", { callbackUrl: "/" })}
        style={{ background: "#1e36b1", border: 0, borderRadius: 6, color: "#fff", cursor: "pointer", fontWeight: 800, minHeight: 40, padding: "0 16px" }}
      >
        Try again
      </button>
    </section>
  )
}

export default function ErrorPage() {
  return (
    <main style={{ display: "grid", minHeight: "100vh", placeItems: "center", padding: 24 }}>
      <Suspense>
        <ErrorContent />
      </Suspense>
    </main>
  )
}
