import "next-auth"
import { JWT } from "next-auth/jwt"

declare module "next-auth" {
  interface Session {
    accessToken?: string
    error?: string
    roles?: string[]
    user: {
      id: string
      name?: string | null
      email?: string | null
      image?: string | null
    }
  }

  interface Profile {
    realm_access?: {
      roles: string[]
    }
    resource_access?: Record<string, { roles?: string[] }>
    preferred_username?: string
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    accessToken?: string
    refreshToken?: string
    expiresAt?: number
    idToken?: string
    roles?: string[]
    error?: string
  }
}

