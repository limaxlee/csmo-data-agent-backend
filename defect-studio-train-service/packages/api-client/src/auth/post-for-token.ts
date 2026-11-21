import type { ApiClient } from '@defect-studio/api-client';
import type { TokenResponse } from './auth.dto';

// Login and refresh do not mutate the shared client: linking uses local credentials
// while the app's ordinary requests must continue using its SSO service token.
export async function postForToken(
  client: ApiClient,
  path: string,
  body: unknown,
): Promise<TokenResponse> {
  return client.request<TokenResponse>(
    path,
    { method: 'POST', body: JSON.stringify(body) },
    false,
  );
}
