import type { ApiClient } from '../utils/api-client';
import type { User } from './auth.dto';

// This client must carry the existing account's local access token.
export function linkSso(client: ApiClient, serviceToken: string): Promise<User> {
  return client.request<User>('/api/auth/sso/link', {
    method: 'POST',
    body: JSON.stringify({ service_token: serviceToken }),
  });
}
