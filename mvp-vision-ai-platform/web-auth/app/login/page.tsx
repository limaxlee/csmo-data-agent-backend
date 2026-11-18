"use client"

import { Suspense, useEffect, useRef, useState } from "react"
import { signIn, signOut, useSession } from "next-auth/react"
import { useSearchParams } from "next/navigation"

const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH || ""

type DevLoginStatus = {
  enabled: boolean
  allowAdmin: boolean
}

function DevLoginForm({
  callbackUrl,
  allowAdmin,
}: {
  callbackUrl: string
  allowAdmin: boolean
}) {
  const [loginid, setLoginid] = useState("")
  const [role, setRole] = useState("user")

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!loginid.trim()) return
    window.location.href = `${BASE_PATH}/dev-login?loginid=${encodeURIComponent(loginid.trim())}&role=${encodeURIComponent(role)}&redirect=${encodeURIComponent(callbackUrl)}`
  }

  return (
    <div style={{ textAlign: "center", maxWidth: 360, width: "100%" }}>
      <div style={{ marginBottom: 24 }}>
        <span style={{ background: "#fef3c7", color: "#92400e", fontSize: 12, fontWeight: 600, padding: "4px 10px", borderRadius: 9999 }}>
          DEV MODE
        </span>
      </div>
      <p style={{ color: "#334155", fontSize: 18, fontWeight: 700, marginBottom: 8 }}>개발 환경 로그인</p>
      <p style={{ color: "#64748b", fontSize: 13, marginBottom: 24 }}>ADFS 없이 loginid로 바로 접속합니다.</p>
      <form  style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <input
          type="text"
          placeholder="loginid (예: stage.user)"
          value={loginid}
           => setLoginid(e.target.value)}
          autoFocus
          style={{
            border: "1px solid #cbd5e1",
            borderRadius: 8,
            fontSize: 14,
            outline: "none",
            padding: "10px 14px",
            width: "100%",
          }}
        />
        {allowAdmin && (
          <select
            value={role}
             => setRole(e.target.value)}
            style={{
              border: "1px solid #cbd5e1",
              borderRadius: 8,
              fontSize: 14,
              outline: "none",
              padding: "10px 14px",
              width: "100%",
              background: "#fff",
            }}
          >
            <option value="user">User</option>
            <option value="admin">Admin</option>
          </select>
        )}
        <button
          type="submit"
          style={{
            background: "#1e36b1",
            border: "none",
            borderRadius: 8,
            color: "#fff",
            cursor: "pointer",
            fontSize: 14,
            fontWeight: 600,
            padding: "10px 0",
          }}
        >
          로그인
        </button>
      </form>
    </div>
  )
}

function LoginContent() {
  const searchParams = useSearchParams()
  const callbackUrl = searchParams?.get("callbackUrl") || process.env.NEXT_PUBLIC_AUTH_DEFAULT_CALLBACK_URL || "/"
  const authError = searchParams?.get("error")
  const { data: session, status } = useSession()
  const authActionStartedRef = useRef(false)
  const [devLoginStatus, setDevLoginStatus] = useState<DevLoginStatus | null>(null)

  useEffect(() => {
    let cancelled = false

    fetch(`${BASE_PATH}/dev-login/status`, {
      cache: "no-store",
      credentials: "same-origin",
    })
      .then((response) => {
        if (!response.ok) throw new Error(`status ${response.status}`)
        return response.json() as Promise<DevLoginStatus>
      })
      .then((result) => {
        if (!cancelled) setDevLoginStatus(result)
      })
      .catch(() => {
        if (!cancelled) setDevLoginStatus({ enabled: false, allowAdmin: false })
      })

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (devLoginStatus === null || devLoginStatus.enabled) return
    // Do not immediately retry a failed provider redirect. That creates an
    // invisible redirect loop and prevents the user from seeing the error.
    if (authError) return

    if (authActionStartedRef.current) {
      return
    }

    if (status === "authenticated") {
      if (session?.error === "RefreshAccessTokenError") {
        authActionStartedRef.current = true
        signOut({ redirect: false }).finally(() => {
          signIn("adfs", { callbackUrl })
        })
        return
      }

      authActionStartedRef.current = true
      window.location.replace(callbackUrl)
      return
    }

    if (status === "unauthenticated") {
      authActionStartedRef.current = true
      signIn("adfs", { callbackUrl })
    }
  }, [status, session?.error, callbackUrl, devLoginStatus, authError])

  if (devLoginStatus?.enabled) {
    return <DevLoginForm callbackUrl={callbackUrl} allowAdmin={devLoginStatus.allowAdmin} />
  }

  if (authError) {
    return (
      <div style={{ maxWidth: 440, textAlign: "center" }}>
        <p style={{ color: "#dc2626", fontSize: 18, fontWeight: 700 }}>SSO 로그인에 실패했습니다.</p>
        <p style={{ color: "#64748b", fontSize: 14 }}>오류 코드: {authError}</p>
        <button
          type="button"
           => signIn("adfs", { callbackUrl })}
          style={{ background: "#1e36b1", border: 0, borderRadius: 6, color: "#fff", cursor: "pointer", fontWeight: 600, minHeight: 40, padding: "0 16px" }}
        >
          다시 로그인
        </button>
      </div>
    )
  }

  return (
    <div style={{ textAlign: "center" }}>
      <div className="spinner" />
      <p style={{ color: "#334155", fontSize: 18, fontWeight: 700, marginTop: 24 }}>Redirecting to SSO login...</p>
      <p style={{ color: "#64748b", fontSize: 14 }}>Please wait a moment.</p>
      <style jsx>{`
        .spinner {
          animation: spin 900ms linear infinite;
          border: 4px solid #dbe4f0;
          border-bottom-color: #1e36b1;
          border-radius: 999px;
          height: 64px;
          margin: 0 auto;
          width: 64px;
        }
        @keyframes spin {
          to {
            transform: rotate(360deg);
          }
        }
      `}</style>
    </div>
  )
}

export default function LoginPage() {
  return (
    <main style={{ display: "grid", minHeight: "100vh", placeItems: "center", padding: 24 }}>
      <Suspense>
        <LoginContent />
      </Suspense>
    </main>
  )
}

