import { beforeEach, describe, expect, it } from 'vitest';
import { server } from '@defect-studio/test-utils/msw-server';
import { screen, waitFor, within } from '@defect-studio/test-utils/react';
import { renderGalleryTab, setupGalleryTest } from '@/test/galleryTestUtils';
import { bytes, grouped, masks, plan, results, withMasks } from '@/mocks/galleryHandlers';

describe('GalleryTab mask visibility', () => {
  beforeEach(setupGalleryTest);

  it('disables mask visibility but still opens image previews when no mask exists', async () => {
    server.use(results([['0', 'a.png']]), bytes());

    const { user } = renderGalleryTab();

    await waitFor(() => expect(screen.getByAltText('a.png')).toBeTruthy());
    expect(screen.queryByRole('group', { name: '마스크' })).toBeNull();
    expect(screen.getByRole('switch', { name: '마스크 표시' }).hasAttribute('disabled')).toBe(true);
    expect(screen.queryByRole('button', { name: '미리보기 열기' })).toBeNull();
    await user.click(screen.getByRole('button', { name: 'a.png' }));
    expect(screen.getByAltText('미리보기: a.png')).toBeTruthy();
  });

  // An older BFF sends no has_mask field; that must read as "no mask".
  it('treats a missing has_mask as no mask', async () => {
    const old = plan('0', ['a.png']);
    server.use(
      grouped([{ ...old, artifacts: old.artifacts.map(({ has_mask: _, ...a }) => a) } as typeof old]),
      bytes(),
    );

    renderGalleryTab();

    await waitFor(() => expect(screen.getByAltText('a.png')).toBeTruthy());
    expect(screen.queryByRole('group', { name: '마스크' })).toBeNull();
    expect(screen.getByRole('switch', { name: '마스크 표시' }).hasAttribute('disabled')).toBe(true);
  });

  it('draws the masks on the thumbnails only while the toggle is on', async () => {
    const asked: string[] = [];
    server.use(grouped([withMasks(plan('0', ['a.png', 'b.png']), ['a.png'])]), masks((p) => asked.push(p)), bytes());

    const { user } = renderGalleryTab();
    const toggle = await screen.findByRole('switch', { name: '마스크 표시' });
    expect(toggle.getAttribute('aria-checked')).toBe('false');
    expect(screen.queryByAltText('마스크: a.png')).toBeNull();
    expect(asked).toEqual([]);

    await user.click(toggle);
    await waitFor(() => expect(screen.getByAltText('마스크: a.png')).toBeTruthy());
    // b.png has no mask, so it is not requested.
    expect(screen.queryByAltText('마스크: b.png')).toBeNull();
    expect(asked).toEqual(['0/a.png']);

    await user.click(toggle);
    expect(screen.queryByAltText('마스크: a.png')).toBeNull();
  });

  it('omits mask counts and toggles masks independently for each plan', async () => {
    server.use(grouped([
      withMasks(plan('1', ['a.png', 'unmasked.png']), ['a.png']),
      withMasks(plan('0', ['b.png']), ['b.png']),
    ]), masks(), bytes());
    const { user } = renderGalleryTab();
    const first = within(await screen.findByRole('region', { name: 'Plan 1' }));
    const second = within(screen.getByRole('region', { name: 'Plan 0' }));

    expect(first.queryByRole('group', { name: '마스크' })).toBeNull();
    expect(second.queryByRole('group', { name: '마스크' })).toBeNull();
    expect(screen.queryByText(/마스크 \(/)).toBeNull();
    const firstToggle = first.getByRole('switch', { name: '마스크 표시' });
    const secondToggle = second.getByRole('switch', { name: '마스크 표시' });
    await user.click(firstToggle);
    expect(await first.findByAltText('마스크: a.png')).toBeTruthy();
    expect(second.queryByAltText('마스크: b.png')).toBeNull();
    expect(secondToggle.getAttribute('aria-checked')).toBe('false');

    await user.click(secondToggle);
    expect(await second.findByAltText('마스크: b.png')).toBeTruthy();
    await user.click(firstToggle);
    expect(first.queryByAltText('마스크: a.png')).toBeNull();
    expect(second.getByAltText('마스크: b.png')).toBeTruthy();
    expect(secondToggle.getAttribute('aria-checked')).toBe('true');
  });
});

