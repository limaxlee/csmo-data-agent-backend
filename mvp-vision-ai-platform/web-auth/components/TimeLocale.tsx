"use client"

import { createContext, useContext, useEffect, useState, type ReactNode } from "react"
import { timeZoneForLocale, type TimeLocale } from "../app/lib/dateTime"

const STORAGE_KEY = "web-auth-time-locale"
const Context = createContext<{ locale: TimeLocale; setLocale: (locale: TimeLocale) => void } | null>(null)

export function TimeLocaleProvider({ children }: { children: ReactNode }) {
  const [locale, updateLocale] = useState<TimeLocale>("ko")
  useEffect(() => {
    const read = () => {
      const saved = window.localStorage.getItem(STORAGE_KEY)
      updateLocale(saved === "en" ? "en" : "ko")
    }
    read()
    window.addEventListener("storage", read)
    return () => window.removeEventListener("storage", read)
  }, [])
  const setLocale = (next: TimeLocale) => {
    window.localStorage.setItem(STORAGE_KEY, next)
    updateLocale(next)
  }
  return <Context.Provider value={{ locale, setLocale }}>{children}</Context.Provider>
}

export function useTimeLocale() {
  const context = useContext(Context)
  if (!context) throw new Error("useTimeLocale requires TimeLocaleProvider")
  return context
}

export function TimeLocaleSelect() {
  const { locale, setLocale } = useTimeLocale()
  return <select aria-label="시간 표시 언어 / Date and time language" title={timeZoneForLocale(locale)}
    value={locale}  => setLocale(event.target.value as TimeLocale)}
    style={{ padding: "6px 8px", border: "1px solid #d1d5db", borderRadius: 6, background: "white", color: "#374151", fontSize: 12 }}>
    <option value="ko">한국어 · 서울</option>
    <option value="en">English · US Eastern</option>
  </select>
}
