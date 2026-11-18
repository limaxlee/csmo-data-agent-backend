import type {
  ActiveTab,
  BackgroundItem,
  ImageInfo,
  ReferenceItem,
} from '@defect-studio/contracts';
import type { ValidationResult } from './appStore.validation';

// 액션을 뺀 값 필드. appStore 의 initialValues() 와 reset() 이 이 타입을 씁니다.
export interface AppStateValues {
  // UI 상태
  activeTab: ActiveTab;
  darkMode: boolean;
  isLoading: boolean;
  sidebarWidth: number;

  // 다중 이미지 + 마스크
  backgrounds: BackgroundItem[];
  references: ReferenceItem[];

  // 현재 편집 중인 인덱스
  currentBgIndex: number;
  currentRefIndex: number;

  // 현재 작업 중인 임시 마스크 (레퍼런스 등록 전)
  tempRefMask: string;
}

export interface AppState extends AppStateValues {
  // Actions - UI
  setActiveTab: (tab: ActiveTab) => void;
  setDarkMode: (dark: boolean) => void;
  setLoading: (loading: boolean) => void;
  setSidebarWidth: (width: number) => void;

  // Actions - 정상 이미지
  addBackgrounds: (images: ImageInfo[]) => void;
  removeBackground: (index: number) => void;
  setCurrentBgIndex: (index: number) => void;

  // Actions - 불량 이미지
  addReferences: (images: ImageInfo[]) => void;
  removeReference: (index: number) => void;
  setCurrentRefIndex: (index: number) => void;
  setTempRefMask: (mask: string) => void;
  registerRefMask: () => void;

  // Actions - 검증
  validateDefectImages: () => ValidationResult;

  // 모든 값 필드를 초기값으로 되돌립니다.
  reset: () => void;
}
