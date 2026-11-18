import { http, HttpResponse } from 'msw';
import { useActiveThreadStore } from '@/features/threads/model/activeThreadStore';
import { beforeEach, describe, expect, it } from 'vitest';
import { server } from '@defect-studio/test-utils/msw-server';
import { screen, waitFor } from '@defect-studio/test-utils/react';
import { renderGalleryTab, setupGalleryTest } from '@/test/galleryTestUtils';
import { PNG, bytes, results } from '@/mocks/galleryHandlers';

describe('GalleryTab data loading', () => {
  beforeEach(setupGalleryTest);

  it('asks the user to open a conversation when none is open', () => {
    useActiveThreadStore.setState({ activeThreadId: null });

    renderGalleryTab();

    expect(screen.getByText('대화를 선택해주세요')).toBeTruthy();
  });

  it('shows the generated images of the open conversation', async () => {
    server.use(results([['0', '0000.png'], ['0', '0001.png']]), bytes());

    renderGalleryTab();

    await waitFor(() => expect(screen.getByAltText('0000.png')).toBeTruthy());
    expect(await screen.findByAltText('0001.png')).toBeTruthy();
    expect(screen.getByRole('heading', { level: 2, name: '생성 이미지 2' })).toBeTruthy();
  });

  it('shows images from every plan', async () => {
    server.use(results([['0', 'a.png'], ['1', 'b.png']]), bytes());

    renderGalleryTab();

    await waitFor(() => expect(screen.getByAltText('a.png')).toBeTruthy());
    expect(screen.getByAltText('b.png')).toBeTruthy();
  });

  // The plan a file belongs to is part of its download path, so a tile that took
  // the wrong plan_id would 404 rather than render.
  it('downloads each image under the plan it belongs to', async () => {
    const asked: string[] = [];
    server.use(
      results([['0', 'a.png'], ['7', 'b.png']]),
      http.get('*/api/threads/t1/plans/:pid/results/:filename', ({ params }) => {
        asked.push(`${params.pid}/${params.filename}`);
        return HttpResponse.arrayBuffer(PNG.buffer, { headers: { 'Content-Type': 'image/png' } });
      }),
    );

    renderGalleryTab();

    await waitFor(() => expect(asked.length).toBe(2));
    expect(asked.sort()).toEqual(['0/a.png', '7/b.png']);
  });

  it('shows the empty state for a conversation that has generated nothing', async () => {
    server.use(results([]));

    renderGalleryTab();

    await waitFor(() => expect(screen.getByText('생성 이미지가 없습니다')).toBeTruthy());
  });

  it('reports an initial failure in Korean without leaking raw HTTP text', async () => {
    server.use(http.get('*/api/threads/t1/results', () => new HttpResponse(null, { status: 500 })));

    renderGalleryTab();

    await waitFor(() =>
      expect(screen.getByText(/이미지 목록을 불러오지 못했습니다/)).toBeTruthy(),
    );
    expect(screen.queryByText(/Agent request failed/)).toBeNull();
    expect(screen.queryByText('생성 이미지가 없습니다')).toBeNull();
  });
});

