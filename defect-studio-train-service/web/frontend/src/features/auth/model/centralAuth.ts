export interface CentralSession {
  authenticated: boolean;
  user: { id: string; name: string | null; email: string | null } | null;
}

export interface ServiceToken {
  accessToken: string;
  tokenType: string;
  expiresAt: number; // Unix seconds, as returned by web-auth.
}

const authBase = (import.meta.env.VITE_AUTH_BASE_URL || '/auth').replace(/\/$/, '');

export class CentralAuthError extends Error {
  constructor(readonly status: number) {
    super('Central authentication failed (' + status + ')');
  }
}

async function centralGet<T>(path: string): Promise<T> {
  const response = await fetch(new URL(authBase + path, window.location.origin), {
    credentials: 'include',
    cache: 'no-store',
  });
  if (!response.ok) throw new CentralAuthError(response.status);
  return response.json() as Promise<T>;
}

export function getCentralSession(): Promise<CentralSession> {
  return centralGet<CentralSession>('/session');
}

let tokenRequest: Promise<ServiceToken> | null = null;

export function getCentralToken(): Promise<ServiceToken> {
  if (!tokenRequest) {
    tokenRequest = centralGet<ServiceToken>('/token').finally(() => { tokenRequest = null; });
  }
  return tokenRequest;
}

export function centralLoginUrl(returnUrl = window.location.href): string {
  const url = new URL(authBase + '/login', window.location.origin);
  url.searchParams.set('callbackUrl', returnUrl);
  return url.toString();
}

export function centralLogoutUrl(): string {
  return new URL(authBase + '/logout', window.location.origin).toString();
}

