"use client"

import { useTimeLocale, TimeLocaleSelect } from "../../components/TimeLocale"
import { formatDateTime } from "../lib/dateTime"
import { useCallback, useEffect, useState, type CSSProperties } from "react"

// platform 백엔드 API (VirtualService 가 /platform/api → platform-backend 로 라우팅)
const PLATFORM_API = process.env.NEXT_PUBLIC_PLATFORM_API_URL || "/platform/api/v1"

interface Profile {
  full_name?: string | null
  email?: string | null
  username?: string | null
  department?: string | null
  company?: string | null
  system_role?: string | null
}

interface ApiToken {
  id: number
  name: string
  token_prefix: string
  created_at: string
  last_used_at?: string | null
  revoked_at?: string | null
}

async function getAccessToken(): Promise<string | null> {
  const res = await fetch("/token", { credentials: "include", cache: "no-store" })
  if (!res.ok) return null
  const data = await res.json()
  return data.accessToken ?? null
}

export default function SettingsPage() {
  const { locale } = useTimeLocale()
  const [token, setToken] = useState<string | null>(null)
  const [profile, setProfile] = useState<Profile | null>(null)
  const [tokens, setTokens] = useState<ApiToken[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [newName, setNewName] = useState("")
  const [creating, setCreating] = useState(false)
  const [issued, setIssued] = useState<string | null>(null) // 평문 토큰 1회 표시
  const [copied, setCopied] = useState(false)

  const authedFetch = useCallback(
    async (path: string, init?: RequestInit) => {
      const bearer = token ?? (await getAccessToken())
      if (!bearer) {
        window.location.href = `/login?callbackUrl=${encodeURIComponent("/settings")}`
        throw new Error("unauthenticated")
      }
      return fetch(`${PLATFORM_API}${path}`, {
        ...init,
        headers: {
          ...(init?.headers || {}),
          Authorization: `Bearer ${bearer}`,
          "Content-Type": "application/json",
        },
      })
    },
    [token],
  )

  const loadTokens = useCallback(async () => {
    const res = await authedFetch("/auth/api-tokens")
    if (res.ok) setTokens(await res.json())
  }, [authedFetch])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const bearer = await getAccessToken()
        if (!bearer) {
          window.location.href = `/login?callbackUrl=${encodeURIComponent("/settings")}`
          return
        }
        if (cancelled) return
        setToken(bearer)

        const [meRes, tokRes] = await Promise.all([
          fetch(`${PLATFORM_API}/auth/me`, { headers: { Authorization: `Bearer ${bearer}` } }),
          fetch(`${PLATFORM_API}/auth/api-tokens`, { headers: { Authorization: `Bearer ${bearer}` } }),
        ])
        if (cancelled) return
        if (meRes.ok) setProfile(await meRes.json())
        if (tokRes.ok) setTokens(await tokRes.json())
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load")
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const handleCreate = async () => {
    const name = newName.trim()
    if (!name) {
      setError("토큰 이름을 입력하세요.")
      return
    }
    setCreating(true)
    setError(null)
    try {
      const res = await authedFetch("/auth/api-tokens", {
        method: "POST",
        body: JSON.stringify({ name }),
      })
      if (!res.ok) {
        setError(`발급 실패 (${res.status})`)
        return
      }
      const data = await res.json()
      setIssued(data.token)
      setCopied(false)
      setNewName("")
      await loadTokens()
    } finally {
      setCreating(false)
    }
  }

  const handleRevoke = async (id: number) => {
    if (!window.confirm("이 토큰을 철회하시겠습니까? 즉시 무효화됩니다.")) return
    const res = await authedFetch(`/auth/api-tokens/${id}`, { method: "DELETE" })
    if (res.ok || res.status === 204) {
      await loadTokens()
    } else {
      setError(`철회 실패 (${res.status})`)
    }
  }

  const copyIssued = async () => {
    if (!issued) return
    try {
      await navigator.clipboard.writeText(issued)
      setCopied(true)
    } catch {
      /* clipboard 권한 없을 수 있음 — 수동 복사 안내 */
    }
  }

  return (
    <main style={S.page}>
      <div style={S.container}>
        <header style={S.header}>
          <a href="/" style={S.brand}>DICE</a>
          <a href="/logout" style={S.logout}>로그아웃</a>
        </header>

        <h1 style={S.title}>사용자 설정</h1>

        {loading ? (
          <p style={S.muted}>불러오는 중…</p>
        ) : (
          <>
            <section style={S.card}>
              <h2 style={S.h2}>프로필</h2>
              <dl style={S.dl}>
                <Row label="이름" value={profile?.full_name || profile?.username} />
                <Row label="이메일" value={profile?.email} />
                <Row label="부서" value={profile?.department} />
                <Row label="회사" value={profile?.company} />
                <Row label="권한" value={profile?.system_role} />
              </dl>
            </section>

            <section style={S.card}>
              <h2 style={S.h2}>API 토큰</h2>
              <TimeLocaleSelect />
              <p style={S.muted}>
                platform·labeler 백엔드를 외부에서 호출할 때 쓰는 개인 토큰입니다.
                만료는 없으며, 필요 시 철회하세요. 토큰은 발급 시 한 번만 표시됩니다.
              </p>

              {issued && (
                <div style={S.issuedBox}>
                  <strong style={{ color: "#92400e" }}>새 토큰이 발급되었습니다 — 지금 복사하세요. 다시 볼 수 없습니다.</strong>
                  <code style={S.issuedCode}>{issued}</code>
                  <div style={{ display: "flex", gap: 8 }}>
                    <button  style={S.btnPrimary}>{copied ? "복사됨 ✓" : "복사"}</button>
                    <button  => setIssued(null)} style={S.btnGhost}>닫기</button>
                  </div>
                </div>
              )}

              <div style={S.createRow}>
                <input
                  value={newName}
                   => setNewName(e.target.value)}
                  placeholder="토큰 이름 (예: ci-pipeline)"
                  style={S.input}
                  onKeyDown={(e) => e.key === "Enter" && handleCreate()}
                />
                <button
                  
                  disabled={creating}
                  style={{ ...S.btnPrimary, ...(creating ? S.btnDisabled : {}) }}
                >
                  {creating ? "발급 중…" : "발급"}
                </button>
              </div>

              {error && <p style={{ color: "#dc2626", fontSize: 14 }}>{error}</p>}

              <table style={S.table}>
                <thead>
                  <tr>
                    <th style={S.th}>이름</th>
                    <th style={S.th}>토큰</th>
                    <th style={S.th}>생성</th>
                    <th style={S.th}>마지막 사용</th>
                    <th style={S.th}>상태</th>
                    <th style={S.th}></th>
                  </tr>
                </thead>
                <tbody>
                  {tokens.length === 0 ? (
                    <tr><td colSpan={6} style={{ ...S.td, color: "#94a3b8" }}>발급된 토큰이 없습니다.</td></tr>
                  ) : (
                    tokens.map((t) => {
                      const revoked = !!t.revoked_at
                      return (
                        <tr key={t.id} style={{ opacity: revoked ? 0.5 : 1 }}>
                          <td style={S.td}>{t.name}</td>
                          <td style={S.td}><code>{t.token_prefix}…</code></td>
                          <td style={S.td}>{formatDateTime(t.created_at, locale)}</td>
                          <td style={S.td}>{formatDateTime(t.last_used_at, locale)}</td>
                          <td style={S.td}>{revoked ? "철회됨" : "활성"}</td>
                          <td style={S.td}>
                            {!revoked && (
                              <button  => handleRevoke(t.id)} style={S.btnDanger}>철회</button>
                            )}
                          </td>
                        </tr>
                      )
                    })
                  )}
                </tbody>
              </table>
            </section>
          </>
        )}
      </div>
    </main>
  )
}

function Row({ label, value }: { label: string; value?: string | null }) {
  return (
    <div style={{ display: "flex", padding: "8px 0", borderBottom: "1px solid #f1f5f9" }}>
      <dt style={{ width: 100, color: "#64748b", fontSize: 14 }}>{label}</dt>
      <dd style={{ margin: 0, color: "#0f172a", fontSize: 14, fontWeight: 600 }}>{value || "—"}</dd>
    </div>
  )
}

const S: Record<string, CSSProperties> = {
  page: { minHeight: "100vh", background: "#f3f6fb", padding: "0 0 64px" },
  container: { maxWidth: 860, margin: "0 auto", padding: "0 24px" },
  header: { display: "flex", justifyContent: "space-between", alignItems: "center", height: 64 },
  brand: { color: "#1f3fbd", fontWeight: 850, fontSize: 18, textDecoration: "none" },
  logout: { color: "#475569", fontSize: 13, fontWeight: 700, textDecoration: "none" },
  title: { fontSize: 28, fontWeight: 900, color: "#0f172a", margin: "16px 0 24px" },
  card: { background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: 24, marginBottom: 20 },
  h2: { fontSize: 18, fontWeight: 800, color: "#0f172a", margin: "0 0 16px" },
  muted: { color: "#64748b", fontSize: 14, lineHeight: 1.6, margin: "0 0 16px" },
  dl: { margin: 0 },
  createRow: { display: "flex", gap: 8, marginBottom: 16 },
  input: { flex: 1, padding: "10px 12px", border: "1px solid #cbd5e1", borderRadius: 8, fontSize: 14 },
  btnPrimary: { background: "#1f3fbd", color: "#fff", border: 0, borderRadius: 8, padding: "10px 18px", fontWeight: 700, fontSize: 14, cursor: "pointer" },
  btnDisabled: { opacity: 0.5, cursor: "not-allowed" },
  btnGhost: { background: "#edf2f8", color: "#334155", border: "1px solid #d8e1ee", borderRadius: 8, padding: "10px 18px", fontWeight: 700, fontSize: 14, cursor: "pointer" },
  btnDanger: { background: "#fef2f2", color: "#dc2626", border: "1px solid #fecaca", borderRadius: 6, padding: "6px 12px", fontWeight: 700, fontSize: 13, cursor: "pointer" },
  table: { width: "100%", borderCollapse: "collapse", fontSize: 14 },
  th: { textAlign: "left", padding: "10px 8px", borderBottom: "2px solid #e2e8f0", color: "#64748b", fontSize: 12, fontWeight: 800 },
  td: { padding: "10px 8px", borderBottom: "1px solid #f1f5f9", color: "#0f172a" },
  issuedBox: { display: "flex", flexDirection: "column", gap: 10, background: "#fffbeb", border: "1px solid #fde68a", borderRadius: 8, padding: 16, marginBottom: 16 },
  issuedCode: { display: "block", wordBreak: "break-all", background: "#fff", border: "1px solid #fde68a", borderRadius: 6, padding: 12, fontSize: 13, color: "#0f172a" },
}
