import { beforeEach, describe, expect, it } from 'vitest';
import { server } from '@defect-studio/test-utils/msw-server';
import { screen, within } from '@defect-studio/test-utils/react';
import { renderGalleryTab, setupGalleryTest } from '@/test/galleryTestUtils';
import { bytes, grouped, plan, results } from '@/mocks/galleryHandlers';

describe('GalleryTab preview controls', () => {
  beforeEach(setupGalleryTest);

  it('opens a clicked image in the preview', async () => {
    server.use(results([['0', 'a.png'], ['0', 'b.png']]), bytes());

    const { user } = renderGalleryTab();
    await user.click(await screen.findByRole('button', { name: 'b.png' }));

    expect(screen.getByAltText('미리보기: b.png')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'b.png', pressed: true })).toBeTruthy();
  });

  // The images are in display order, so 다음 moves into the next (older) generation.
  it('steps from one generation to the next with 다음', async () => {
    server.use(grouped([plan('1', ['b.png']), plan('0', ['a.png'])]), bytes());

    const { user } = renderGalleryTab();
    await user.click(await screen.findByRole('button', { name: 'b.png' }));
    expect(screen.getByText('1 / 2')).toBeTruthy();

    await user.click(screen.getByRole('button', { name: '다음 이미지' }));
    expect(screen.getByAltText('미리보기: a.png')).toBeTruthy();
  });

  it('closes the preview from its header and reopens it from a thumbnail', async () => {
    server.use(grouped([plan('0', ['a.png', 'b.png'])]), bytes());
    const { user } = renderGalleryTab();
    const region = within(await screen.findByRole('region', { name: 'Plan 0' }));

    expect(screen.queryByRole('button', { name: '닫기' })).toBeNull();
    await user.click(await region.findByRole('button', { name: 'a.png' }));
    expect(screen.getByAltText('미리보기: a.png')).toBeTruthy();
    await user.click(screen.getByRole('button', { name: '다음 이미지' }));
    expect(screen.getByAltText('미리보기: b.png')).toBeTruthy();

    await user.click(screen.getByRole('button', { name: '닫기' }));
    expect(screen.queryByAltText('미리보기: b.png')).toBeNull();
    expect(screen.queryByRole('separator', { name: '미리보기 너비 조절' })).toBeNull();
    expect(screen.queryAllByRole('button', { pressed: true })).toHaveLength(0);
    await user.click(region.getByRole('button', { name: 'a.png' }));
    expect(screen.getByAltText('미리보기: a.png')).toBeTruthy();
  });

  it('replaces the current preview when another plan image is clicked', async () => {
    server.use(grouped([plan('1', ['a.png']), plan('0', ['b.png', 'c.png'])]), bytes());
    const { user } = renderGalleryTab();
    const first = within(await screen.findByRole('region', { name: 'Plan 1' }));
    const second = within(screen.getByRole('region', { name: 'Plan 0' }));

    await user.click(await first.findByRole('button', { name: 'a.png' }));
    await user.click(await second.findByRole('button', { name: 'b.png' }));

    expect(screen.queryByAltText('미리보기: a.png')).toBeNull();
    expect(screen.getByAltText('미리보기: b.png')).toBeTruthy();
    expect(first.getByRole('button', { name: 'a.png', pressed: false })).toBeTruthy();
    expect(screen.getAllByRole('button', { pressed: true })).toHaveLength(1);

    await user.click(screen.getByRole('button', { name: '닫기' }));
    expect(screen.queryByAltText('미리보기: b.png')).toBeNull();
  });
});

