import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { BackgroundItem, ReferenceItem } from '@defect-studio/contracts';
import type { AppState, AppStateValues } from './appStore.types';
import { validateDefectImages } from './appStore.validation';
import { clampWidth } from '@/shared/lib/clampWidth';

export const SIDEBAR_MIN_WIDTH = 180;
export const SIDEBAR_MAX_WIDTH = 480;
export const SIDEBAR_DEFAULT_WIDTH = 224;

// 상수가 아니라 함수입니다. darkMode 는 localStorage 를 읽으므로, 모듈이 로드될 때
// 한 번 계산해두면 localStorage.clear() 뒤에 reset() 을 부를 때 옛 값이 남습니다.
const initialValues = (): AppStateValues => ({
  activeTab: 'agent',
  darkMode: localStorage.getItem('darkMode') === 'true',
  isLoading: false,
  sidebarWidth: SIDEBAR_DEFAULT_WIDTH,

  backgrounds: [],
  references: [],
  currentBgIndex: 0,
  currentRefIndex: 0,
  tempRefMask: '',
});

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      ...initialValues(),

      reset: () => set(initialValues()),

      // UI Actions
      setActiveTab: (tab) => set({ activeTab: tab }),
      setDarkMode: (dark) => {
        localStorage.setItem('darkMode', String(dark));
        set({ darkMode: dark });
      },
      setLoading: (loading) => set({ isLoading: loading }),
      setSidebarWidth: (width) => set({
        sidebarWidth: clampWidth(width, SIDEBAR_MIN_WIDTH, SIDEBAR_MAX_WIDTH),
      }),

      // 정상 이미지 Actions
      addBackgrounds: (images) => set((state) => {
        const newItems: BackgroundItem[] = images.map(img => ({
          id: `bg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          image: img,
        }));
        return {
          backgrounds: [...state.backgrounds, ...newItems],
          currentBgIndex: state.backgrounds.length === 0 ? 0 : state.currentBgIndex,
        };
      }),

      removeBackground: (index) => set((state) => {
        const newBackgrounds = state.backgrounds.filter((_, i) => i !== index);
        let newIndex = state.currentBgIndex;
        if (newIndex >= newBackgrounds.length) {
          newIndex = Math.max(0, newBackgrounds.length - 1);
        }
        return { backgrounds: newBackgrounds, currentBgIndex: newIndex };
      }),

      setCurrentBgIndex: (index) => set({ currentBgIndex: index }),

      // 불량 이미지 Actions
      addReferences: (images) => set((state) => {
        const newItems: ReferenceItem[] = images.map(img => ({
          id: `ref-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          image: img,
          mask: null,
        }));
        return {
          references: [...state.references, ...newItems],
          currentRefIndex: state.references.length === 0 ? 0 : state.currentRefIndex,
        };
      }),

      removeReference: (index) => set((state) => {
        const newReferences = state.references.filter((_, i) => i !== index);
        let newIndex = state.currentRefIndex;
        if (newIndex >= newReferences.length) {
          newIndex = Math.max(0, newReferences.length - 1);
        }
        return {
          references: newReferences,
          currentRefIndex: newIndex,
          tempRefMask: '',
        };
      }),

      setCurrentRefIndex: (index) => set({
        currentRefIndex: index,
        tempRefMask: '',
      }),

      setTempRefMask: (mask) => set({ tempRefMask: mask }),

      registerRefMask: () => set((state) => {
        if (!state.tempRefMask || state.references.length === 0) return state;

        const newReferences = [...state.references];
        const current = newReferences[state.currentRefIndex];
        if (current) {
          newReferences[state.currentRefIndex] = {
            ...current,
            mask: state.tempRefMask,
          };
        }

        return {
          references: newReferences,
          tempRefMask: '',
        };
      }),

      // 검증 (순수 함수로 분리 — appStore.validation.ts)
      validateDefectImages: () => validateDefectImages(get()),
    }),
    {
      name: 'defect-studio-storage',
      version: 2,
      // v1 persisted training flags, generation params and the active task. Those
      // features are gone — strip them so old browsers don't rehydrate dead keys.
      migrate: (persisted) => {
        if (persisted && typeof persisted === 'object') {
          const clone = { ...(persisted as Record<string, unknown>) };
          for (const key of ['maskTrainingDone', 'defectTrainingDone', 'trainingJobs', 'params', 'currentTask']) {
            delete clone[key];
          }
          return clone;
        }
        return persisted;
      },
      partialize: (state) => ({
        backgrounds: state.backgrounds,
        references: state.references,
        currentBgIndex: state.currentBgIndex,
        currentRefIndex: state.currentRefIndex,
        darkMode: state.darkMode,
        sidebarWidth: state.sidebarWidth,
      }),
    }
  )
);

