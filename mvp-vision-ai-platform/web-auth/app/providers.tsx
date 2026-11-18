"use client"

import { TimeLocaleProvider } from "../components/TimeLocale"
import { SessionProvider } from "next-auth/react"

export function Providers({ children }: { children: React.ReactNode }) {
  const rawBasePath = process.env.NEXT_PUBLIC_BASE_PATH || "/"
  // Normalize: "/" -> "", "/foo" -> "/foo"
  const basePath = rawBasePath === "/" ? "/api/auth" : `${rawBasePath}/api/auth`

  return <SessionProvider basePath={basePath}><TimeLocaleProvider>{children}</TimeLocaleProvider></SessionProvider>
}
