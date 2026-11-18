import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest';
import { transferableAbortController } from 'node:util';
import { http, HttpResponse } from 'msw';
import { server } from '@defect-studio/test-utils/msw-server';
import { fireEvent, screen, waitFor } from '@defect-studio/test-utils/react';
import { renderApp, setupAppTest } from '@/test/appTestUtils';
import { TEST_THREAD_ID } from '@/mocks/agentHandlers';
import { useActiveThreadStore } from '@/features/threads/model/activeThreadStore';

describe('App native upload workflow', () => {
  beforeEach(() => { setupAppTest(); vi.stubGlobal('AbortController', transferableAbortController); });
  afterEach(() => vi.unstubAllGlobals());
  it.each([
    ['불량 이미지', 'defect'], ['정상 이미지', 'normal'],
  ])('uses native images and uploads in the %s tab without feature flags', async (tab, category) => {
    let legacyCalls = 0;
    const roles: string[] = [];
    server.use(
      http.get('*/api/threads/:thread/native-data', ({ request }) => {
        roles.push(new URL(request.url).searchParams.get('category') ?? '');
        return HttpResponse.json({ items: [], total: 0, defect_count: 0, masked_count: 0, status: 'not_uploaded' });
      }),
      http.get('*/api/threads/:thread/train-data', () => {
        legacyCalls++; return HttpResponse.json({ files: [], status: null });
      }),
    );
    useActiveThreadStore.setState({ activeThreadId: TEST_THREAD_ID });
    renderApp();
    fireEvent.click(await screen.findByRole('button', { name: '테스트 대화' }));
    fireEvent.click(screen.getByRole('button', { name: tab }));
    await waitFor(() => expect((screen.getByLabelText('이미지 또는 ZIP 파일') as HTMLInputElement).disabled).toBe(false));
    expect(screen.getByLabelText('이미지 폴더')).toBeTruthy();
    await waitFor(() => expect(roles).toContain(category));
    expect(legacyCalls).toBe(0);

    // Main locks to viewport height so the right preview/mask editor stays fixed in view.
    const main = document.querySelector('main') as HTMLElement;
    expect(main.className).toContain('overflow-hidden');
    expect(main.className).not.toContain('overflow-y-auto');
    expect((main.firstElementChild as HTMLElement).className).toContain('h-full');
  });
});

