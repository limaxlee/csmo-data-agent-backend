'use client'

// Shared top bar (brand mark + nav links + user menu / login button) used by
// the landing page and any other web-auth page that wants the same chrome
// (e.g. /downloads) instead of rolling its own header. Self-contained: sets
// its own --primary/--line custom properties so it renders correctly outside
// of LandingPage's .dice-landing scope too.

import React from 'react'
import { TimeLocaleSelect } from './TimeLocale'
import { useDashboardLink, withDashboardLink } from './useDashboardLink'

export interface SiteHeaderNavLink {
  label: string
  href: string
}

export interface SiteHeaderProps {
  navLinks: SiteHeaderNavLink[]
  isAuthenticated?: boolean
  userName?: string | null
  onLogin?: () => void
  onLogout?: () => void
  settingsHref?: string
  hideAuthAction?: boolean
}

export default function SiteHeader({
  navLinks,
  isAuthenticated,
  userName,
  onLogin,
  onLogout,
  hideAuthAction = false,
  settingsHref = `${(process.env.NEXT_PUBLIC_BASE_PATH || '').replace(/\/+$/, '')}/settings`,
}: SiteHeaderProps) {
  const dashboardHref = useDashboardLink(!!isAuthenticated, userName)
  const [userMenuOpen, setUserMenuOpen] = React.useState(false)
  const userMenuRef = React.useRef<HTMLDivElement | null>(null)

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
    const  MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setUserMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [])

  return (
    <div className="site-header-root">
      <style dangerouslySetInnerHTML={{ __html: STYLES }} suppressHydrationWarning />
      <header className="dice-header">
        <a href={`${(process.env.NEXT_PUBLIC_BASE_PATH || '').replace(/\/+$/, '')}/`} className="dice-brand">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img className="dice-brand-combined" src={`${(process.env.NEXT_PUBLIC_BASE_PATH || '').replace(/\/+$/, '')}/dice_symbolNlettermark.png`} alt="DICE" />
        </a>
        <nav className="dice-nav">
          {withDashboardLink(navLinks, dashboardHref).map((link, index, list) => (
            <React.Fragment key={link.label}>
              <a href={link.href}>{link.label}</a>
              {link.label === 'Defect' && index < list.length - 1 ? (
                <span className="dice-nav-divider" aria-hidden="true" />
              ) : null}
            </React.Fragment>
          ))}
        </nav>
        <div className="dice-header-actions">
          <TimeLocaleSelect />
          {hideAuthAction ? null : isAuthenticated ? (
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
                      onLogout?.()
                    }}
                  >
                    로그아웃
                  </button>
                </div>
              ) : null}
            </div>
          ) : (
            <button  className="site-header-login-btn" type="button">
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
    justify-content: space-between;
    left: 0;
    padding: 0 48px;
    position: sticky;
    right: 0;
    top: 0;
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
`

