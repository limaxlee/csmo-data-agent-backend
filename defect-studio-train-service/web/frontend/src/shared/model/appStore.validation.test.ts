import { beforeEach, describe, expect, it } from 'vitest';
import { TEST_MASK_DATA_URL, createReferenceItem } from '@defect-studio/test-utils/fixtures';
import { setupStoreTest } from '@/test/storeTestUtils';
import { useAppStore } from './appStore';

describe('useAppStore validation gating', () => {
  beforeEach(setupStoreTest);

  describe('validateDefectImages', () => {
    it('is invalid when no reference images are uploaded', () => {
      expect(useAppStore.getState().validateDefectImages()).toEqual({
        valid: false,
        errors: ['불량 이미지를 업로드해주세요.', '불량 이미지에 마스크를 등록해주세요.'],
      });
    });

    it('is invalid when a reference image has no mask', () => {
      useAppStore.setState({ references: [createReferenceItem({ mask: null })] });

      expect(useAppStore.getState().validateDefectImages()).toEqual({
        valid: false,
        errors: ['불량 이미지 1번에 마스크를 등록해주세요.'],
      });
    });

    it('groups unmasked reference indices into a single message', () => {
      useAppStore.setState({
        references: [
          createReferenceItem({ mask: null }),
          createReferenceItem({ mask: TEST_MASK_DATA_URL }),
          createReferenceItem({ mask: null }),
        ],
      });

      expect(useAppStore.getState().validateDefectImages()).toEqual({
        valid: false,
        errors: ['불량 이미지 1, 3번에 마스크를 등록해주세요.'],
      });
    });

    it('is valid with masked references even when no backgrounds are uploaded', () => {
      useAppStore.setState({
        backgrounds: [],
        references: [createReferenceItem({ mask: TEST_MASK_DATA_URL })],
      });

      expect(useAppStore.getState().validateDefectImages()).toEqual({ valid: true, errors: [] });
    });
  });
});
