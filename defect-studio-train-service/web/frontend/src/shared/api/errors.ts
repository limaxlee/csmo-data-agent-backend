import { ApiError } from '@defect-studio/api-client';
import { logClientWarn } from '@/shared/lib/clientLogger';

// Shared store error helpers. errMsg normalizes a thrown value to a raw string for
// diagnostic logs; userErrorMessage returns a user-friendly Korean message while
// logging raw HTTP/transport details to the browser console.
export const errMsg = (e: unknown): string => (e instanceof Error ? e.message : 'Request failed');

export const NO_THREAD_SELECTED = '스레드를 먼저 선택하세요.';

export const DEFAULT_USER_ERROR = '일시적인 서버 통신 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.';

const HAS_KOREAN = /[가-힣]/;

function isCleanKoreanMessage(text: string): boolean {
  const trimmed = text.trim();
  if (!trimmed || !HAS_KOREAN.test(trimmed)) return false;
  if (trimmed.startsWith('Agent request failed:')) return false;
  if (trimmed.startsWith('<!DOCTYPE') || trimmed.startsWith('<html')) return false;
  return true;
}

export function userErrorMessage(
  error: unknown,
  fallback: string = DEFAULT_USER_ERROR,
  context = 'api.request_failed',
): string {
  if (error instanceof ApiError) {
    logClientWarn(context, {
      status: error.status,
      statusText: error.statusText,
      body: error.body.slice(0, 300),
    });
    try {
      const parsed = JSON.parse(error.body) as {
        detail?: unknown;
        message?: unknown;
        error?: { message?: unknown };
      };
      const candidate = parsed.error?.message ?? parsed.message ?? parsed.detail;
      if (typeof candidate === 'string' && isCleanKoreanMessage(candidate)) {
        return candidate.trim();
      }
    } catch {
      // Non-JSON body; keep raw body in console log only.
    }
    return fallback;
  }

  if (typeof error === 'string') {
    if (isCleanKoreanMessage(error)) return error.trim();
    logClientWarn(context, { error });
    return fallback;
  }

  if (error instanceof Error) {
    if (isCleanKoreanMessage(error.message)) return error.message.trim();
    logClientWarn(context, { error: error.message });
    return fallback;
  }

  logClientWarn(context, { error: String(error) });
  return fallback;
}
