import type { ApiClient } from '@defect-studio/api-client';
import type { LoginRequest, TokenResponse } from './auth.dto';
import { postForToken } from './post-for-token';

export async function login(client: ApiClient, body: LoginRequest): Promise<TokenResponse> {
  return postForToken(client, '/api/auth/login', body);
}