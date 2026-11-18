import type { AppState } from './appStore.types';

export interface ValidationResult {
  valid: boolean;
  errors: string[];
}

// Indices (1-based) of items still missing a mask, grouped into one message.
const unmaskedMessage = (missing: number[], noun: string): string | null =>
  missing.length > 0 ? `${noun} ${missing.join(', ')}번에 마스크를 등록해주세요.` : null;

// 불량 이미지 준비 조건: 마스크가 등록된 불량 이미지가 하나 이상 있어야 함.
export function validateDefectImages(state: Pick<AppState, 'references'>): ValidationResult {
  const errors: string[] = [];

  if (state.references.length === 0) {
    errors.push('불량 이미지를 업로드해주세요.');
    errors.push('불량 이미지에 마스크를 등록해주세요.');
  } else {
    const missing = state.references
      .map((ref, i) => (ref.mask ? null : i + 1))
      .filter((n): n is number => n !== null);
    const message = unmaskedMessage(missing, '불량 이미지');
    if (message) errors.push(message);
  }

  return { valid: errors.length === 0, errors };
}

