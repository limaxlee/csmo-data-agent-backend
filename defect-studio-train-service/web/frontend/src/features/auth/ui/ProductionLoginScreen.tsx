import { useEffect, useRef, useState } from 'react';
import { Button } from '@defect-studio/ui';
import { useAuthStore } from '../model/authStore';
import { centralLoginUrl } from '../model/centralAuth';
import { markSsoRedirectAttempt, tryAutomaticSsoLogin } from '../model/ssoRedirect';

export function ProductionLoginScreen() {
  const status = useAuthStore((state) => state.status);
  const error = useAuthStore((state) => state.error);
  const [redirecting, setRedirecting] = useState(status === 'signed-out');
  const attempted = useRef(false);
  useEffect(() => {
    if (status === 'signed-out' && !attempted.current) {
      attempted.current = true;
      setRedirecting(tryAutomaticSsoLogin());
    }
  }, [status]);

  return <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 dark:bg-dark-300">
    <div className="flex w-full max-w-sm flex-col gap-4 rounded-2xl bg-white p-8 shadow-sm dark:bg-dark-200">
      <h1 className="text-lg font-bold text-primary-600">DefectAgent</h1>
      {redirecting ? <p role="status">Samsung SSO 로그인으로 이동하고 있습니다…</p> : <>
        {status === 'error' || status === 'unlinked'
          ? <p role="alert">{error ?? 'SSO 계정을 준비하지 못했습니다. 다시 시도하거나 관리자에게 문의해 주세요.'}</p>
          : <p>SSO 로그인 결과를 확인하지 못했습니다. 다시 로그인해 주세요.</p>}
        <a href={centralLoginUrl()} 
          className="rounded-lg bg-primary-600 px-4 py-2 text-center font-medium text-white">SSO 로그인 다시 시도</a>
        <Button type="button" variant="text"  => void useAuthStore.getState().bootstrap()}>로그인 상태 다시 확인</Button>
      </>}
    </div>
  </div>;
}
