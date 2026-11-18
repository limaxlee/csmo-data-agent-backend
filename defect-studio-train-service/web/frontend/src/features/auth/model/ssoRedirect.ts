import { centralLoginUrl } from './centralAuth';

const ATTEMPT = 'defect-studio-sso-redirect-attempt';

export function clearSsoRedirectAttempt(): void {
  sessionStorage.removeItem(ATTEMPT);
}

// Also suppress immediate re-login while an explicit logout is navigating away.
export function markSsoRedirectAttempt(): void {
  sessionStorage.setItem(ATTEMPT, '1');
}

export function tryAutomaticSsoLogin(
  navigate: (url: string) => void = (url) => window.location.replace(url),
): boolean {
  if (sessionStorage.getItem(ATTEMPT)) return false;
  markSsoRedirectAttempt();
  navigate(centralLoginUrl());
  return true;
}
