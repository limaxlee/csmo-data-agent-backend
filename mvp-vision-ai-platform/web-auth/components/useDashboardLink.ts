"use client"

import { useEffect, useState } from "react"

export function useDashboardLink(isAuthenticated: boolean, userName?: string | null): string | null {
  const key = userName || ""
  const [access, setAccess] = useState<{ key: string; href: string } | null>(null)
  useEffect(() => {
    setAccess(null)
    if (!isAuthenticated) return
    let disposed = false
    let pending: AbortController | null = null
    async function check() {
      pending?.abort()
      const controller = new AbortController()
      pending = controller
      setAccess(null)
      try {
        const base = (process.env.NEXT_PUBLIC_BASE_PATH || "").replace(/\/+$/, "")
        const response = await fetch(`${base}/dashboard-access`, {
          credentials: "include", cache: "no-store", signal: controller.signal,
        })
        if (!response.ok) return
        const body = await response.json()
        if (!disposed && !controller.signal.aborted && body?.isAdmin === true && typeof body.href === "string") {
          const target = new URL(body.href, window.location.origin)
          if (["http:", "https:"].includes(target.protocol)) setAccess({ key, href: body.href })
        }
      } catch {
        // A missing profile never grants menu access or redirects a public page.
      }
    }
    const  => { if (document.visibilityState === "visible") void check() }
    void check()
    const interval = window.setInterval(onFocus, 30_000)
    window.addEventListener("focus", onFocus)
    document.addEventListener("visibilitychange", onFocus)
    return () => {
      disposed = true
      pending?.abort()
      window.clearInterval(interval)
      window.removeEventListener("focus", onFocus)
      document.removeEventListener("visibilitychange", onFocus)
    }
  }, [isAuthenticated, key])
  return isAuthenticated && access?.key === key ? access.href : null
}

export function withDashboardLink<T extends { label: string; href: string }>(links: T[], href: string | null) {
  const visible: Array<{ label: string; href: string }> = links.filter(
    link => link.label !== "Dashboard" && link.label !== "Admin",
  )
  if (href) {
    visible.push({ label: "Admin", href })
  }
  return visible
}
