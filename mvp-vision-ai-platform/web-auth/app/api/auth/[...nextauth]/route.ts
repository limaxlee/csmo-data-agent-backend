import NextAuth, { NextAuthOptions } from "next-auth"
import { JWT } from "next-auth/jwt"
import { isAllowedCallbackOrigin } from "../../../auth-origin"

const isProduction = process.env.NODE_ENV === "production"
const adfsIssuerInternal = process.env.ADFS_ISSUER_INTERNAL || process.env.ADFS_ISSUER
const adfsIssuerPublic = process.env.ADFS_ISSUER || adfsIssuerInternal

// ADFS v4.0 Authorization Code + PKCE flow (standard, no hybrid)
// response_mode=form_post 는 cross-site POST 로 SameSite=Lax 쿠키를 차단하므로 사용하지 않음
// redirect_uri 는 NEXTAUTH_URL 에서 자동 계산 (NextAuth 기본 동작)
function createADFSProvider() {
  const authBase = (adfsIssuerPublic || "").trim().replace(/\/$/, "")

  return {
    id: "adfs",
    name: "ADFS",
    type: "oauth" as const,
    clientId: process.env.ADFS_CLIENT_ID!,
    // 빈 문자열은 omit — public client(PKCE only) 구성 시 ADFS 가 client_secret 거부함
    clientSecret: process.env.ADFS_CLIENT_SECRET?.trim(),
    // authBase 를 사용해 후행 슬래시 제거 — issuer mismatch 방지
    issuer: authBase,
    wellKnown: `${authBase}/.well-known/openid-configuration`,
    authorization: {
      url: `${authBase}/oauth2/authorize`,
      params: {
        // ADFS v4.0 Hybrid Flow: authorize 응답에 code + id_token 동시 수신
        // response_type 은 space-separated (URL 인코딩: code%20id_token)
        // ADFS 는 code%20id_token 과 code+id_token 모두 허용
        response_type: "code id_token",
        response_mode: "form_post",
        scope: "openid email profile",
      },
    },
    token: `${authBase}/oauth2/token`,
    userinfo: `${authBase}/userinfo`,
    // nonce: authorize/token 양쪽 id_token 의 nonce 클레임 검증
    checks: ["state" as const, "nonce" as const],
    // profile 은 userinfo 응답을 받지만 ADFS 는 upn/unique_name/sid 를
    // id_token 에만 포함하므로 jwt 콜백에서 id_token 직접 디코딩해 보강함
    profile: (profile: any) => {
      return {
        id: profile.sub,
        name: profile.upn || profile.unique_name || profile.name,
        email: profile.upn || profile.email,
        unique_name: profile.unique_name,
        sid: profile.sid,
        roles: profile.groups || profile.role || [],
      }
    },
  }
}

function normalizeBasePath(value: string | undefined): string {
  const raw = (value || "").trim()
  if (!raw || raw === "/") return ""
  return `/${raw.replace(/^\/+|\/+$/g, "")}`
}

function resolveAuthBaseUrl(fallbackUrl: string): string {
  const rawAuthUrl = (process.env.NEXTAUTH_URL || "").trim().replace(/\/+$/, "")
  if (!rawAuthUrl) return fallbackUrl
  if (rawAuthUrl.endsWith("/api/auth")) {
    const appUrl = rawAuthUrl.slice(0, -"/api/auth".length)
    return appUrl || new URL(rawAuthUrl).origin
  }
  return rawAuthUrl
}

function allowedCallbackPrefixes(): string[] {
  const raw = process.env.AUTH_ALLOWED_CALLBACK_PREFIXES || "/,/platform,/labeler"
  return raw
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean)
}

function isAllowedRelativeCallback(pathname: string): boolean {
  // Allow auth pages without checks
  if (pathname === "/login" || pathname === "/error") return true

  return allowedCallbackPrefixes().some((prefix) => {
    if (prefix === "/") return pathname === "/"
    return pathname === prefix || pathname.startsWith(`${prefix}/`)
  })
}

function resolveRedirectUrl(url: string, baseUrl: string): string {
  // Use explicitly configured NEXTAUTH_URL if available, ensuring correct hostname
  // even if NextAuth computed baseUrl from localhost due to missing X-Forwarded-* headers
  const configuredUrl = process.env.NEXTAUTH_URL?.trim().replace(/\/+$/, "")
  const base = new URL(configuredUrl || baseUrl)
  const authBasePath = normalizeBasePath(process.env.NEXT_PUBLIC_BASE_PATH || "/")

  if (url.startsWith("/")) {
    if (url.startsWith(`${authBasePath}/`) || isAllowedRelativeCallback(url)) {
      return `${base.origin}${url}`
    }
    return base.origin
  }

  const target = new URL(url)
  if (target.origin === base.origin) return url
  if (isAllowedCallbackOrigin(target.origin)) return url
  return base.origin
}

const authOptions: NextAuthOptions = {
  secret: process.env.NEXTAUTH_SECRET,
  debug: process.env.NEXTAUTH_DEBUG === "true",
  providers: [
    createADFSProvider(),
  ],
  pages: {
    signIn: `${normalizeBasePath(process.env.NEXT_PUBLIC_BASE_PATH || "/")}/login`,
    error: `${normalizeBasePath(process.env.NEXT_PUBLIC_BASE_PATH || "/")}/error`,
  },
  session: {
    strategy: "jwt",
    maxAge: 60 * 60,
  },
  callbacks: {
    async jwt({ token, account, profile }) {
      if (account) {
        token.accessToken = account.access_token
        token.refreshToken = account.refresh_token
        token.expiresAt = account.expires_at
        token.idToken = account.id_token

        // ADFS 는 upn/unique_name/sid 를 id_token 에만 포함하고
        // userinfo endpoint 에는 표준 OIDC 클레임만 반환하는 경우가 많음.
        // id_token payload 를 직접 디코딩해 ADFS 전용 클레임을 보강.
        let idTokenClaims: Record<string, any> = {}
        if (account.id_token) {
          try {
            const payload = account.id_token.split(".")[1]
            idTokenClaims = JSON.parse(Buffer.from(payload, "base64url").toString())
          } catch {
            // 디코딩 실패 시 profile 만으로 진행
          }
        }

        // id_token 클레임이 userinfo 보다 우선 (ADFS 전용 필드)
        const claims = { ...(profile as any), ...idTokenClaims }

        const adfsGroups = claims.groups || []
        const adfsRole = claims.role || []
        const allRoles = [
          ...(Array.isArray(adfsGroups) ? adfsGroups : [adfsGroups].filter(Boolean)),
          ...(Array.isArray(adfsRole) ? adfsRole : [adfsRole].filter(Boolean)),
        ]
        token.roles = Array.from(new Set(allRoles))
        token.name = claims.upn || claims.unique_name || claims.sub || "unknown"
        if (claims.upn) token.email = claims.upn
        if (claims.unique_name) token.unique_name = claims.unique_name
        if (claims.sid) token.sid = claims.sid
      }

      if (token.error === "RefreshAccessTokenError") {
        return token
      }

      if (token.expiresAt && Date.now() < (token.expiresAt as number) * 1000) {
        return token
      }

      return refreshAccessToken(token)
    },

    async session({ session, token }) {
      session.accessToken = token.accessToken as string
      session.error = token.error as string | undefined
      session.roles = (token.roles as string[]) || []

      if (session.user) {
        session.user.id = token.sub as string
      }

      return session
    },

    async redirect({ url, baseUrl }) {
      return resolveRedirectUrl(url, baseUrl)
    },
  },
  events: {
    async signOut({ token }) {
      if (!token?.idToken) return

      // ADFS logout endpoint
      const logoutUrl = `${adfsIssuerInternal}/oauth2/logout`
      const params = new URLSearchParams({
        id_token_hint: token.idToken as string,
        post_logout_redirect_uri: resolveAuthBaseUrl("http://localhost:3020"),
      })

      try {
        await fetch(`${logoutUrl}?${params}`)
      } catch (error) {
        console.error("Failed to logout from ADFS:", error)
      }
    },
  },
  cookies: {
    sessionToken: {
      name: "dice.session-token",
      options: { httpOnly: true, sameSite: "lax" as const, path: "/", secure: isProduction, domain: process.env.COOKIE_DOMAIN },
    },
    callbackUrl: {
      name: "dice.callback-url",
      options: { httpOnly: true, sameSite: "lax" as const, path: "/", secure: isProduction, domain: process.env.COOKIE_DOMAIN },
    },
    csrfToken: {
      name: "dice.csrf-token",
      options: { httpOnly: true, sameSite: "lax" as const, path: "/", secure: isProduction, domain: process.env.COOKIE_DOMAIN },
    },
    state: {
      name: "dice.state",
      options: { httpOnly: true, sameSite: "none" as const, path: "/", secure: isProduction, maxAge: 900, domain: process.env.COOKIE_DOMAIN },
    },
    nonce: {
      name: "dice.nonce",
      options: { httpOnly: true, sameSite: "none" as const, path: "/", secure: isProduction, domain: process.env.COOKIE_DOMAIN },
    },
  },
}

async function refreshAccessToken(token: JWT): Promise<JWT> {
  const refreshToken = token.refreshToken
  if (!refreshToken) {
    return { ...token, error: "RefreshAccessTokenError" }
  }

  // ADFS token endpoint
  const tokenEndpoint = `${adfsIssuerInternal}/oauth2/token`
  const maxRetries = 2

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const response = await fetch(tokenEndpoint, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({
          client_id: process.env.ADFS_CLIENT_ID!,
          client_secret: process.env.ADFS_CLIENT_SECRET || "",
          grant_type: "refresh_token",
          refresh_token: refreshToken as string,
        }),
      })

      const refreshedTokens = await response.json()

      if (!response.ok) {
        if (response.status === 400 || response.status === 401) {
          throw refreshedTokens
        }
        if (attempt < maxRetries) {
          await new Promise((resolve) => setTimeout(resolve, 1000 * (attempt + 1)))
          continue
        }
        throw refreshedTokens
      }

      return {
        ...token,
        accessToken: refreshedTokens.access_token,
        expiresAt: Math.floor(Date.now() / 1000) + refreshedTokens.expires_in,
        refreshToken: refreshedTokens.refresh_token ?? token.refreshToken,
        idToken: refreshedTokens.id_token ?? token.idToken,
      }
    } catch (error) {
      if (attempt < maxRetries && !(error as any)?.error) {
        await new Promise((resolve) => setTimeout(resolve, 1000 * (attempt + 1)))
        continue
      }
      console.error("Error refreshing access token:", error)
      return { ...token, error: "RefreshAccessTokenError" }
    }
  }

  return { ...token, error: "RefreshAccessTokenError" }
}

const handler = NextAuth(authOptions)

export { handler as GET, handler as POST }

