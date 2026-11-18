import type { ReactNode } from 'react';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it } from 'vitest';
import { server, setupMswServer } from '@defect-studio/test-utils/msw-server';
import { renderHook, waitFor } from '@defect-studio/test-utils/react';
import { Providers } from '@/app/Providers';
import { apiClient } from '@/shared/api/apiClient';
import { queryClient } from '@/shared/api/queryClient';
import { useAuthedObjectURL } from '@/shared/lib/useAuthedObjectURL';

setupMswServer();

const wrapper = ({ children }: { children: ReactNode }) => <Providers>{children}</Providers>;

describe('useAuthedObjectURL', () => {
  beforeEach(() => {
    apiClient.setToken('access-abc');
    queryClient.clear();
  });

  it('sends one request for a file id even after the component unmounts and mounts again', async () => {
    let requests = 0;
    server.use(
      http.get('*/api/threads/thread-1/train-data/f1', () => {
        requests += 1;
        return new HttpResponse('<svg xmlns="http://www.w3.org/2000/svg" />', {
          headers: { 'Content-Type': 'image/svg+xml' },
        });
      }),
    );

    const first = renderHook(() => useAuthedObjectURL('thread-1', 'f1'), { wrapper });
    await waitFor(() => expect(first.result.current.url).not.toBe(''));
    expect(requests).toBe(1);
    first.unmount();

    const second = renderHook(() => useAuthedObjectURL('thread-1', 'f1'), { wrapper });
    await waitFor(() => expect(second.result.current.url).not.toBe(''));
    expect(requests).toBe(1);
  });
});
