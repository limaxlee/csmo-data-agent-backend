'use client'

// Docs-site's copy of web-auth's SiteHeader (components/SiteHeader.tsx there).
// docs-site is a fully separate Next.js app/build, so this can't be a shared
// import — kept as a self-contained copy instead. Differences from the
// web-auth version: fetches its own session and admin-only Dashboard link
// through a small same-origin server proxy, and isn't position:sticky.

import React from 'react'
import { usePathname, useRouter } from 'next/navigation'
import diceLogo from '../public/dice_symbolNlettermark.png'

// middleware.ts's locale-detection matcher only excludes a fixed allowlist of
// static files (favicon.ico, dice_icon.png, _next/static, ...) — a raw
// `src="/docs/dice_symbolNlettermark.png"` string falls outside that list and
// gets 307-redirected to a locale-prefixed path that 404s. Importing the file
// as a module routes it through /_next/static/media instead, which *is*
// excluded, so it loads regardless of what the matcher does or doesn't know
// about this specific filename.

export interface SiteHeaderNavLink {
  label: string
  href: string
}

export interface SiteHeaderProps {
  navLinks: SiteHeaderNavLink[]
  settingsHref?: string
}

interface Session {
  authenticated: boolean
  user: { name?: string | null; email?: string | null } | null
}

export default function SiteHeader({ navLinks, settingsHref = '/settings' }: SiteHeaderProps) {
  const [session, setSession] = React.useState<Session | null>(null)
  const [dashboardHref, setDashboardHref] = React.useState<string | null>(null)
  const [userMenuOpen, setUserMenuOpen] = React.useState(false)
  const userMenuRef = React.useRef<HTMLDivElement | null>(null)

  const pathname = usePathname() || ''
  const router = useRouter()

  // usePathname() omits the configured /docs basePath. Match the internal route: /{lang}/{product}/... or /{lang}/{product}/archive/{version}/...
  const match = pathname.match(/^\/(ko|en)\/(runner|labeler|platform)(?:\/archive\/([^\/]+))?(\/(.*))?$/)

  const showVersionSelector = !!match
  const currentLang = match ? match[1] : 'ko'
  const currentProduct = match ? match[2] : ''
  const currentVersion = match && match[3] ? match[3] : 'latest'
  const currentSubPath = match ? match[5] || '' : ''

  // Product-specific versions configuration
  const productVersions: Record<string, { label: string; value: string }[]> = {
    runner: [
      { label: currentLang === 'en' ? 'Latest version (Current)' : '최신 버전 (Current)', value: 'latest' },
      { label: currentLang === 'en' ? 'August 2026' : '2026년 8월호', value: '2026-08' },
    ],
    labeler: [
      { label: currentLang === 'en' ? 'Latest version (Current)' : '최신 버전 (Current)', value: 'latest' },
      { label: currentLang === 'en' ? 'August 2026' : '2026년 8월호', value: '2026-08' },
    ],
    platform: [
      { label: currentLang === 'en' ? 'Latest version (Current)' : '최신 버전 (Current)', value: 'latest' },
      { label: currentLang === 'en' ? 'August 2026' : '2026년 8월호', value: '2026-08' },
    ]
  }

  const versions = currentProduct ? productVersions[currentProduct] || [] : []

  const handleVersionChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const targetVersion = e.target.value
    if (!currentProduct) return

    let targetPath = ''
    if (targetVersion === 'latest') {
      targetPath = `/${currentLang}/${currentProduct}/${currentSubPath}`
    } else {
      targetPath = `/${currentLang}/${currentProduct}/archive/${targetVersion}/${currentSubPath}`
    }

    targetPath = targetPath.replace(/\/+$/, '')
    router.push(targetPath, { scroll: false })
  }

  React.useEffect(() => {
    let disposed = false
    let pending: AbortController | null = null
    const checkAccess = async () => {
      pending?.abort()
      const controller = new AbortController()
      pending = controller
      setDashboardHref(null)
      try {
        const response = await fetch('/api/auth/session', {
          credentials: 'include', cache: 'no-store', signal: controller.signal,
        })
        const data: Session | null = response.ok ? await response.json() : null
        if (disposed || controller.signal.aborted) return
        setSession(data)
        if (!data?.authenticated) return

        const accessResponse = await fetch('/api/auth/dashboard-access', {
          credentials: 'include', cache: 'no-store', signal: controller.signal,
        })
        if (!accessResponse.ok) return
        const access = await accessResponse.json()
        if (disposed || controller.signal.aborted || access?.isAdmin !== true || typeof access.href !== 'string') return
        const target = new URL(access.href, window.location.origin)
        if (['http:', 'https:'].includes(target.protocol)) setDashboardHref(access.href)
      } catch {
        if (!disposed && !controller.signal.aborted) setSession(null)
      }
    }
    const onFocus = () => { if (document.visibilityState === 'visible') void checkAccess() }
    void checkAccess()
    const interval = window.setInterval(onFocus, 30_000)
    window.addEventListener('focus', onFocus)
    document.addEventListener('visibilitychange', onFocus)
    return () => {
      disposed = true
      pending?.abort()
      window.clearInterval(interval)
      window.removeEventListener('focus', onFocus)
      document.removeEventListener('visibilitychange', onFocus)
    }
  }, [])

  const isAuthenticated = !!session?.authenticated
  const userName = session?.user?.name || session?.user?.email || null
  const visibleNavLinks = navLinks.filter((link) => link.label !== 'Admin' && link.label !== 'Dashboard')
  if (isAuthenticated && dashboardHref) visibleNavLinks.push({ label: 'Admin', href: dashboardHref })

  const userInitials = React.useMemo(() => {
    const raw = (userName || '').trim()
    if (!raw) return 'U'
    const local = raw.includes('@') ? raw.split('@')[0] : raw
    const parts = local.split(/[.\-_\s]+/).filter(Boolean)
    const letters = parts.length >= 2 ? parts[0][0] + parts[1][0] : local.slice(0, 2)
    return letters.toUpperCase()
  }, [userName])

  React.useEffect(() => {
    if (typeof window === 'undefined') return undefined
    const onClick = (e: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setUserMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [])

  const currentPath = () =>
    typeof window === 'undefined' ? '/docs' : `${window.location.pathname}${window.location.search}`

  return (
    <div className="site-header-root">
      <style dangerouslySetInnerHTML={{ __html: STYLES }} suppressHydrationWarning />
      <header className="dice-header">
        <a href="/" className="dice-brand">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img className="dice-brand-combined" src={diceLogo.src} alt="DICE" />
        </a>
        <nav className="dice-nav">
          {visibleNavLinks.map((link, index, list) => (
            <React.Fragment key={link.label}>
              <a href={link.href}>{link.label}</a>
              {link.label === 'Defect' && index < list.length - 1 ? (
                <span className="dice-nav-divider" aria-hidden="true" />
              ) : null}
            </React.Fragment>
          ))}
        </nav>
        <div className="dice-header-actions">
          {showVersionSelector && versions.length > 0 && (
            <div className="dice-version-selector-container">
              <span className="dice-version-label">{currentLang === 'en' ? 'Document version:' : '문서 버전:'}</span>
              <select
                className="dice-version-select"
                value={currentVersion}
                
              >
                {versions.map((ver) => (
                  <option key={ver.value} value={ver.value}>
                    {ver.label}
                  </option>
                ))}
              </select>
            </div>
          )}
          {isAuthenticated ? (
            <div className="dice-user" ref={userMenuRef}>
              <button
                type="button"
                className="dice-user-badge"
                aria-haspopup="menu"
                aria-expanded={userMenuOpen}
                title={userName ?? undefined}
                 => setUserMenuOpen((v) => !v)}
              >
                {userInitials}
              </button>
              {userMenuOpen ? (
                <div className="dice-user-menu" role="menu">
                  <div className="dice-user-menu-id">{userName}</div>
                  <a href={settingsHref} className="dice-user-menu-item" role="menuitem">
                    설정
                  </a>
                  <button
                    type="button"
                    className="dice-user-menu-item danger"
                    role="menuitem"
                     => {
                      setUserMenuOpen(false)
                      window.location.href = '/logout'
                    }}
                  >
                    로그아웃
                  </button>
                </div>
              ) : null}
            </div>
          ) : (
            <button
               => {
                window.location.href = `/login?callbackUrl=${encodeURIComponent(currentPath())}`
              }}
              className="site-header-login-btn"
              type="button"
            >
              로그인
            </button>
          )}
        </div>
      </header>
    </div>
  )
}

const STYLES = `
  .site-header-root {
    --primary: #1f3fbd;
    --line: #d8e1ee;
    font-family: Inter, Pretendard, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  }

  .dice-header {
    align-items: center;
    background: rgba(255, 255, 255, 0.94);
    border-bottom: 1px solid var(--line);
    display: flex;
    gap: 28px;
    height: 64px;
    padding: 0 48px;
    justify-content: space-between;
    z-index: 20;
  }

  .dice-brand {
    align-items: center;
    color: var(--primary);
    display: inline-flex;
    font-size: 18px;
    font-weight: 850;
    letter-spacing: 0;
    white-space: nowrap;
  }

  .dice-brand-combined {
    display: inline-block;
    height: 44px;
    width: auto;
    object-fit: contain;
  }

  .dice-nav {
    align-items: center;
    display: flex;
    gap: 26px;
    justify-content: center;
    margin-left: auto;
  }

  .dice-nav a {
    color: #334155;
    font-size: 15px;
    font-weight: 700;
    line-height: 1;
    text-decoration: none;
  }

  .dice-nav a:hover {
    color: var(--primary);
  }

  .dice-nav-divider {
    align-self: stretch;
    background: #cbd5e1;
    flex-shrink: 0;
    margin: 2px 0;
    width: 1px;
  }

  .dice-header-actions {
    align-items: center;
    display: flex;
    gap: 14px;
  }

  .dice-user {
    position: relative;
  }

  .dice-user-badge {
    align-items: center;
    background: var(--primary);
    border: 0;
    border-radius: 999px;
    color: #fff;
    cursor: pointer;
    display: inline-flex;
    font-size: 13px;
    font-weight: 800;
    height: 38px;
    justify-content: center;
    letter-spacing: 0.3px;
    transition: transform 160ms ease, box-shadow 160ms ease;
    width: 38px;
  }

  .dice-user-badge:hover {
    box-shadow: 0 4px 14px rgba(31, 63, 189, 0.35);
    transform: translateY(-1px);
  }

  .dice-user-menu {
    background: #fff;
    border: 1px solid var(--line);
    border-radius: 12px;
    box-shadow: 0 18px 44px rgba(15, 23, 42, 0.16);
    min-width: 200px;
    overflow: hidden;
    padding: 6px;
    position: absolute;
    right: 0;
    top: calc(100% + 10px);
    z-index: 30;
  }

  .dice-user-menu-id {
    color: #64748b;
    font-size: 12px;
    font-weight: 700;
    overflow: hidden;
    padding: 8px 12px 10px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .dice-user-menu-item {
    background: transparent;
    border: 0;
    border-radius: 8px;
    color: #334155;
    cursor: pointer;
    display: block;
    font-size: 14px;
    font-weight: 700;
    padding: 10px 12px;
    text-align: left;
    text-decoration: none;
    width: 100%;
  }

  .dice-user-menu-item:hover {
    background: #eef2fb;
  }

  .dice-user-menu-item.danger {
    color: #dc2626;
  }

  .dice-user-menu-item.danger:hover {
    background: #fef2f2;
  }

  .site-header-login-btn {
    align-items: center;
    background: var(--primary);
    border: 0;
    border-radius: 999px;
    color: #fff;
    cursor: pointer;
    display: inline-flex;
    font-size: 15px;
    font-weight: 850;
    justify-content: center;
    min-height: 44px;
    padding: 0 22px;
    transition: transform 180ms ease, background 180ms ease, border-color 180ms ease;
    white-space: nowrap;
  }

  .site-header-login-btn:hover {
    transform: translateY(-2px);
  }

  @media (max-width: 820px) {
    .dice-header {
      gap: 14px;
      height: auto;
      padding: 12px 20px;
    }
    .dice-nav {
      display: none;
    }
    .dice-header-actions {
      gap: 8px;
    }
    .site-header-login-btn {
      display: none;
    }
  }

  @media (max-width: 520px) {
    .dice-brand {
      font-size: 16px;
    }
  }

  .dice-version-selector-container {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-right: 16px;
    font-size: 14px;
    color: #4a5568;
  }
  .dice-version-label {
    font-weight: 500;
    white-space: nowrap;
  }
  .dice-version-select {
    padding: 6px 12px;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    background-color: #ffffff;
    color: #1a202c;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    outline: none;
    transition: all 0.2s ease;
  }
  .dice-version-select:hover {
    border-color: #3b82f6;
    background-color: #f8fafc;
  }
  .dice-version-select:focus {
    border-color: #3b82f6;
    box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
  }
`
