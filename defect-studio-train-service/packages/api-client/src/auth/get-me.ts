import type { ApiClient } from '@defect-studio/api-client';
import type { User } from './auth.dto';

export async function getMe(client: ApiClient): Promise<User> {
  return client.request<User>('/api/auth/me', { method: 'GET' });
}