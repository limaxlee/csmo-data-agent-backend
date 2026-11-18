"use client"

import { useEffect } from "react"
import { useSearchParams } from "next/navigation"
import { Suspense } from "react"

function LogoutSuccessContent() {
  const searchParams = useSearchParams()
  const redirectParam = searchParams?.get("redirect")

  useEffect(() => {
    const performLogout = async () => {
      console.log("[logout-success] Clearing session cookies...")

      try {
        await fetch("/api/auth/signout", { method: "POST" })
      } catch (err) {
        console.error("[logout-success] signout error:", err)
      }

      // Clear all cookies to prevent infinite loops
      const cookies = document.cookie.split(";")
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i]
        const eqPos = cookie.indexOf("=")
        const name = eqPos > -1 ? cookie.substr(0, eqPos).trim() : cookie.trim()

        if (name) {
          document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 UTC;path=/;`
          document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 UTC;path=/;domain=${window.location.hostname};`
        }
      }

      await new Promise((resolve) => setTimeout(resolve, 200))

      // Redirect to platform with callback URL for login
      const redirectUrl = redirectParam || (
        process.env.NEXT_PUBLIC_PLATFORM_BASE_PATH
          ? `${process.env.PLATFORM_URL || process.env.NEXT_PUBLIC_AUTH_BASE_URL}${process.env.NEXT_PUBLIC_PLATFORM_BASE_PATH}`
          : `${process.env.PLATFORM_URL || process.env.NEXT_PUBLIC_AUTH_BASE_URL || "http://10.240.245.202:3020"}`
      )
      console.log("[logout-success] Redirecting to:", redirectUrl)
      window.location.replace(redirectUrl)
    }

    performLogout()
  }, [redirectParam])

  return (
    <main style={{ display: "grid", minHeight: "100vh", placeItems: "center", padding: 24, textAlign: "center" }}>
      <section>
        <p style={{ color: "#1e36b1", fontSize: 18, fontWeight: 800 }}>Signing out...</p>
        <p style={{ color: "#64748b" }}>Clearing session and returning to login.</p>
      </section>
    </main>
  )
}

export default function LogoutSuccessPage() {
  return (
    <Suspense fallback={null}>
      <LogoutSuccessContent />
    </Suspense>
  )
}
