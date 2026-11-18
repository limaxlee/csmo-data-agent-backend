import { beforeEach, describe, expect, it } from 'vitest';
import { createImageInfo } from '@defect-studio/test-utils/fixtures';
import { setupStoreTest } from '@/test/storeTestUtils';
import { useAppStore } from './appStore';

describe('useAppStore upload state', () => {
  beforeEach(setupStoreTest);

  it('adds and removes background images while keeping the current index in range', () => {
    const store = useAppStore.getState();

    store.addBackgrounds([
      createImageInfo({ id: 'background-a' }),
      createImageInfo({ id: 'background-b' }),
    ]);
    useAppStore.getState().setCurrentBgIndex(1);
    useAppStore.getState().removeBackground(1);

    const state = useAppStore.getState();
    expect(state.backgrounds).toHaveLength(1);
    expect(state.backgrounds[0].image.id).toBe('background-a');
    expect(state.currentBgIndex).toBe(0);
  });
});
