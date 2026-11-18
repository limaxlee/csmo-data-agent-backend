export type DevLoginRole = "admin" | "user"

export type DevLoginConfig = {
  enabled: boolean
  allowAdmin: boolean
  allowedLoginIds: ReadonlySet<string>
}

function enabled(value: string | undefined): boolean {
  return value?.trim().toLowerCase() === "true"
}

export function normalizeDevLoginId(value: string | undefined | null): string {
  return (value || "").trim().toLowerCase()
}

export function readDevLoginConfig(
  env: Readonly<Record<string, string | undefined>> = process.env,
): DevLoginConfig {
  const allowedLoginIds = new Set(
    (env.DEV_LOGIN_ALLOWED_IDS || "")
      .split(",")
      .map(normalizeDevLoginId)
      .filter(Boolean),
  )

  return {
    // Fail closed: setting only DEV_LOGIN_ENABLED must never expose an
    // arbitrary-user login endpoint.
    enabled: enabled(env.DEV_LOGIN_ENABLED) && allowedLoginIds.size > 0,
    allowAdmin: enabled(env.DEV_LOGIN_ALLOW_ADMIN),
    allowedLoginIds,
  }
}

export function authorizeDevLogin(
  loginId: string | undefined | null,
  requestedRole: string | undefined | null,
  config: DevLoginConfig = readDevLoginConfig(),
): { loginId: string; role: DevLoginRole } | null {
  const normalized = normalizeDevLoginId(loginId)
  if (!config.enabled || !config.allowedLoginIds.has(normalized)) return null

  return {
    loginId: normalized,
    role: requestedRole === "admin" && config.allowAdmin ? "admin" : "user",
  }
}

