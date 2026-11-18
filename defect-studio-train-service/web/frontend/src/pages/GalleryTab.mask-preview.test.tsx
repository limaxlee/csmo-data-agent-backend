import { beforeEach, describe, expect, it } from 'vitest';
import { server } from '@defect-studio/test-utils/msw-server';
import { screen, waitFor, within } from '@defect-studio/test-utils/react';
import { renderGalleryTab, setupGalleryTest } from '@/test/galleryTestUtils';
import { bytes, grouped, masks, plan, withMasks } from '@/mocks/galleryHandlers';

describe('GalleryTab preview masks', () => {
  beforeEach(setupGalleryTest);

  // With the toggle off, the preview's mask is transparent until the pointer is over
  // the panel. jsdom does not apply :hover styles, so this checks the class instead.
  it('shows the preview mask only on hover while the toggle is off', async () => {
    server.use(grouped([withMasks(plan('0', ['a.png']), ['a.png'])]), masks(), bytes());

    const { user } = renderGalleryTab();
    await user.click(await screen.findByRole('button', { name: 'a.png' }));
    const previewMask = await screen.findByAltText('마스크: a.png');
    expect(previewMask.className).toContain('opacity-0');

    await user.click(screen.getByRole('switch', { name: '마스크 표시' }));
    // The thumbnail now draws its mask too, with the same alt text.
    await waitFor(() => expect(screen.getAllByAltText('마스크: a.png')).toHaveLength(2));
    for (const mask of screen.getAllByAltText('마스크: a.png')) {
      expect(mask.className).not.toContain('opacity-0');
    }
  });

  it('draws the mask in the preview of an image that has one', async () => {
    server.use(grouped([withMasks(plan('0', ['a.png', 'b.png']), ['a.png'])]), masks(), bytes());

    const { user } = renderGalleryTab();
    await user.click(await screen.findByRole('button', { name: 'a.png' }));

    expect(await screen.findByAltText('마스크: a.png')).toBeTruthy();
    expect(screen.getByText('마스크')).toBeTruthy();

    await user.click(screen.getByRole('button', { name: '다음 이미지' }));
    expect(screen.getByAltText('미리보기: b.png')).toBeTruthy();
    expect(screen.queryByAltText('마스크: b.png')).toBeNull();
    expect(screen.queryByText('마스크')).toBeNull();
  });

  it('uses the selected plan visibility when preview navigation crosses into another plan', async () => {
    server.use(grouped([
      withMasks(plan('1', ['a.png']), ['a.png']),
      withMasks(plan('0', ['b.png']), ['b.png']),
    ]), masks(), bytes());
    const { user } = renderGalleryTab();
    const first = within(await screen.findByRole('region', { name: 'Plan 1' }));
    const second = within(screen.getByRole('region', { name: 'Plan 0' }));

    await user.click(first.getByRole('switch', { name: '마스크 표시' }));
    await user.click(await first.findByRole('button', { name: /^a\.png/ }));
    await waitFor(() => expect(screen.getAllByAltText('마스크: a.png')).toHaveLength(2));
    for (const mask of screen.getAllByAltText('마스크: a.png')) {
      expect(mask.className).not.toContain('opacity-0');
    }

    await user.click(screen.getByRole('button', { name: '다음 이미지' }));
    const previewMask = await screen.findByAltText('마스크: b.png');
    expect(previewMask.className).toContain('opacity-0');
    expect(first.getByRole('button', { name: /^a\.png/, pressed: false })).toBeTruthy();
    expect(second.getByRole('button', { name: 'b.png', pressed: true })).toBeTruthy();
    expect(second.getByRole('switch', { name: '마스크 표시' }).getAttribute('aria-checked')).toBe('false');

    await user.click(second.getByRole('switch', { name: '마스크 표시' }));
    expect(previewMask.className).not.toContain('opacity-0');
  });
});

