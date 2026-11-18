import { beforeEach, describe, expect, it } from 'vitest';
import { TEST_MASK_DATA_URL, createImageInfo } from '@defect-studio/test-utils/fixtures';
import { setupStoreTest } from '@/test/storeTestUtils';
import { useAppStore } from './appStore';

describe('useAppStore reference state', () => {
  beforeEach(setupStoreTest);

  it('adds references, registers the active reference mask, and clears temporary masks when switching', () => {
    const store = useAppStore.getState();

    store.addReferences([
      createImageInfo({ id: 'reference-a' }),
      createImageInfo({ id: 'reference-b' }),
    ]);
    useAppStore.getState().setTempRefMask(TEST_MASK_DATA_URL);
    useAppStore.getState().setCurrentRefIndex(1);
    useAppStore.getState().setTempRefMask('second-mask');
    useAppStore.getState().registerRefMask();

    const state = useAppStore.getState();
    expect(state.references).toHaveLength(2);
    expect(state.references[0].mask).toBeNull();
    expect(state.references[1].mask).toBe('second-mask');
    expect(state.tempRefMask).toBe('');
  });

  it('removes references while keeping the current reference index in range', () => {
    useAppStore.setState({
      references: [
        {
          id: 'reference-a',
          image: createImageInfo({ id: 'reference-a' }),
          mask: TEST_MASK_DATA_URL,
        },
        {
          id: 'reference-b',
          image: createImageInfo({ id: 'reference-b' }),
          mask: TEST_MASK_DATA_URL,
        },
      ],
      currentRefIndex: 1,
      tempRefMask: 'draft-mask',
    });

    useAppStore.getState().removeReference(1);

    const state = useAppStore.getState();
    expect(state.references).toHaveLength(1);
    expect(state.references[0].image.id).toBe('reference-a');
    expect(state.currentRefIndex).toBe(0);
    expect(state.tempRefMask).toBe('');
  });
});
