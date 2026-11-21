import type { ApiClient } from '../utils/api-client';
import type { User } from './auth.dto';

// This client must carry the central service token.
export function provisionSso(client: ApiClient): Promise<User> {
  return client.request<User>('/api/auth/sso/provision', { method: 'POST' });
}
