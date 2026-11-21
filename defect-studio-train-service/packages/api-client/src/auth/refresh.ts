import type { ApiClient } from '@defect-studio/api-client';
import type { TokenResponse } from './auth.dto';
import { postForToken } from './post-for-token';

export async function refresh(client: ApiClient, refreshToken: string): Promise<TokenResponse> {
  return postForToken(client, '/api/auth/refresh', { refresh_token: refreshToken });
}