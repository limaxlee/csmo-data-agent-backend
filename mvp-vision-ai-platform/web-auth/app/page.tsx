'use client'

import React, { useEffect, useState } from 'react'
import LandingPage from '../components/LandingPage'

const AUTH_BASE = (process.env.NEXT_PUBLIC_BASE_PATH || '').replace(/\/+$/, '')

export default function WebHomePage() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [userName, setUserName] = useState<string | null>(null)

  useEffect(() => {
    checkSession()
    
    // 30 초마다 세션 확인 (탭이 활성화된 경우)
    const interval = setInterval(() => {
      if (document.visibilityState === 'visible') {
        checkSession()
      }
    }, 30000)
    
    return () => clearInterval(interval)
  }, [])

  const checkSession = async () => {
    try {
      // platform/labeler 와 동일하게 web-auth 커스텀 /session 엔드포인트로 통일.
      // /session 은 refresh 실패(RefreshAccessTokenError) 시 authenticated:false 를
      // 반환하므로 만료된 세션을 정확히 로그아웃 상태로 반영함.
      const response = await fetch(`${AUTH_BASE}/session`, {
        credentials: 'include',
        cache: 'no-store'
      })

      if (!response.ok) {
        setIsAuthenticated(false)
        setUserName(null)
        return
      }

      const session = await response.json()

      if (session.authenticated) {
        setIsAuthenticated(true)
        setUserName(session.user?.name || session.user?.email || null)
      } else {
        setIsAuthenticated(false)
        setUserName(null)
      }
    } catch (error) {
      console.error('Session check failed:', error)
      setIsAuthenticated(false)
      setUserName(null)
    }
  }

  const handleLogin = () => {
    // ADFS 로그인 페이지로 리다이렉트
    window.location.href = `${AUTH_BASE}/login?callbackUrl=${encodeURIComponent(window.location.href)}`
  }

  const handleLogout = () => {
    // platform/labeler 와 동일하게 web-auth /logout 으로 통일.
    // /logout 이 ADFS SSO 세션 종료 + 로컬 세션 쿠키 제거를 함께 수행한다.
    window.location.href = `${AUTH_BASE}/logout`
  }

  return (
    <>
      <LandingPage 
        lang="ko" 
        isAuthenticated={isAuthenticated}
        userName={userName}
        
        
      />
    </>
  )
}
