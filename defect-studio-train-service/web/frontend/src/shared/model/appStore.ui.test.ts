import { beforeEach, describe, expect, it } from 'vitest';
import { setupStoreTest } from '@/test/storeTestUtils';
import { useAppStore } from './appStore';

describe('useAppStore UI state', () => {
  beforeEach(setupStoreTest);

  it('persists dark mode changes to localStorage', () => {
    useAppStore.getState().setDarkMode(true);

    expect(useAppStore.getState().darkMode).toBe(true);
    expect(localStorage.getItem('darkMode')).toBe('true');

    useAppStore.getState().setDarkMode(false);

    expect(useAppStore.getState().darkMode).toBe(false);
    expect(localStorage.getItem('darkMode')).toBe('false');
  });
});
