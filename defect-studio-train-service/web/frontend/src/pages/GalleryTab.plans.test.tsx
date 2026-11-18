import { beforeEach, describe, expect, it } from 'vitest';
import { server } from '@defect-studio/test-utils/msw-server';
import { screen, waitFor } from '@defect-studio/test-utils/react';
import { renderGalleryTab, setupGalleryTest } from '@/test/galleryTestUtils';
import { bytes, grouped, plan } from '@/mocks/galleryHandlers';

describe('GalleryTab plan metadata', () => {
  beforeEach(setupGalleryTest);

  it('labels each generation with the plan it ran', async () => {
    server.use(grouped([plan('2', ['a.png'])]), bytes());

    renderGalleryTab();

    await waitFor(() => expect(screen.getByText('Plan 2')).toBeTruthy());
    expect(screen.getByText('1장 · 위치 무작위 · 크기 보통 · 이미지 전체')).toBeTruthy();
    expect(screen.getByText('이미지 1장')).toBeTruthy();
    expect(screen.getByText('생성 완료')).toBeTruthy();
  });

  it('shows when the generation ran and how long it took', async () => {
    server.use(grouped([plan('0', ['a.png'])]), bytes());

    renderGalleryTab();

    // GALLERY_AT_5 to GALLERY_AT_6 is fourteen minutes.
    await waitFor(() => expect(screen.getByText(/14분/)).toBeTruthy());
  });

  it('puts each generation in its own box', async () => {
    server.use(grouped([plan('1', ['b.png']), plan('0', ['a.png'])]), bytes());

    renderGalleryTab();

    await waitFor(() => expect(screen.getByAltText('b.png')).toBeTruthy());
    expect(screen.getByText('Plan 1')).toBeTruthy();
    expect(screen.getByText('Plan 0')).toBeTruthy();
    const headings = screen.getAllByRole('heading', { level: 3 })
      .map((h) => h.textContent)
      .filter((text) => text?.startsWith('Plan'));
    expect(headings).toEqual(['Plan 1', 'Plan 0']);
  });

  it('counts images in the header, not generations', async () => {
    server.use(grouped([plan('1', ['a.png', 'b.png']), plan('0', ['c.png'])]), bytes());

    renderGalleryTab();

    await waitFor(() => expect(screen.getByRole('heading', { level: 2, name: '생성 이미지 3' })).toBeTruthy());
  });

  // run_id is ON DELETE SET NULL on the BFF side, so a group can arrive without
  // times. Rendering them anyway would print "Invalid Date" over the images.
  it('shows a generation whose run is gone, without a time line', async () => {
    server.use(
      grouped([plan('0', ['a.png'], { started_at: null, completed_at: null })]),
      bytes(),
    );

    renderGalleryTab();

    await waitFor(() => expect(screen.getByAltText('a.png')).toBeTruthy());
    expect(screen.queryByText(/Invalid Date/)).toBeNull();
  });

  it('shows the images of a plan whose settings are missing', async () => {
    server.use(grouped([plan('0', ['a.png'], { content: null, status: null })]), bytes());

    renderGalleryTab();

    await waitFor(() => expect(screen.getByAltText('a.png')).toBeTruthy());
    expect(screen.getByText('Plan 0')).toBeTruthy();
  });
});
