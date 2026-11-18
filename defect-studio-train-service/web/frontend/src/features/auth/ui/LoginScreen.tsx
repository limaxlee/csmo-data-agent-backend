import { useState, type FormEvent } from 'react';
import { Zap } from 'lucide-react';
import { ApiClient, ApiError, linkSso, login, provisionSso } from '@defect-studio/api-client';
import { Button, Input } from '@defect-studio/ui';
import { apiClient } from '@/shared/api/apiClient';
import { useAuthStore } from '@/features/auth/model/authStore';
import {
  centralLoginUrl, centralLogoutUrl,
} from '@/features/auth/model/centralAuth';
import { ProductionLoginScreen } from './ProductionLoginScreen';

function accountError(error: unknown): string {
  if (error instanceof ApiError && error.status === 409) {
    try {
      const code = (JSON.parse(error.body) as { code?: string }).code;
      if (code === 'sso_email_mismatch') {
        return '두 계정의 이메일이 다릅니다. 관리자에게 계정 연결을 요청해 주세요.';
      }
      if (code === 'sso_account_conflict') {
        return '이미 사용 중인 계정입니다. 관리자에게 계정 연결을 요청해 주세요.';
      }
    } catch { /* Use the generic message below. */ }
  }
  if (error instanceof ApiError && error.status === 401) {
    return '로그인 정보가 올바르지 않거나 만료되었습니다. 다시 시도해 주세요.';
  }
  return '요청을 완료하지 못했습니다. 다시 시도하거나 관리자에게 문의해 주세요.';
}

export function LoginScreen() {
  return import.meta.env.VITE_DEPLOYMENT_ENV === 'production'
    ? <ProductionLoginScreen /> : <LegacyLoginScreen />;
}

function LegacyLoginScreen() {
  const status = useAuthStore((s) => s.status);
  const statusError = useAuthStore((s) => s.error);
  const [showLink, setShowLink] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [actionError, setActionError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submitLink = async (event: FormEvent) => {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setActionError(null);
    try {
      const serviceToken = await useAuthStore.getState().getBearer();
      if (!serviceToken) throw new Error('No SSO token');
      const local = await login(new ApiClient(), { email, password });
      const user = await linkSso(new ApiClient({ token: local.access_token }), serviceToken);
      useAuthStore.getState().setSsoUser(user);
    } catch (error) {
      setActionError(accountError(error));
    } finally {
      setBusy(false);
    }
  };

  const createAccount = async () => {
    if (busy) return;
    setBusy(true);
    setActionError(null);
    try {
      const user = await provisionSso(apiClient);
      useAuthStore.getState().setSsoUser(user);
    } catch (error) {
      setActionError(accountError(error));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-dark-300 px-4">
      <div className="w-full max-w-sm bg-white dark:bg-dark-200 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-800 p-8 flex flex-col gap-5">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-500 to-indigo-600 flex items-center justify-center">
            <Zap size={20} className="text-white" />
          </div>
          <h1 className="text-lg font-bold text-primary-600">DefectAgent</h1>
        </div>

        {status === 'unlinked' ? (
          <>
            <p>Samsung 계정은 확인됐지만 DefectAgent 계정이 아직 연결되지 않았습니다.</p>
            <Button type="button" variant="primary"  => setShowLink(true)}>
              기존 계정 연결
            </Button>
            {showLink && (
              <form  className="flex flex-col gap-3">
                <label className="flex flex-col gap-1">기존 계정 이메일
                  <Input variant="form" type="email" value={email}  => setEmail(e.target.value)}
                    autoComplete="username" required />
                </label>
                <label className="flex flex-col gap-1">기존 계정 비밀번호
                  <Input variant="form" type="password" value={password}  => setPassword(e.target.value)}
                    autoComplete="current-password" required />
                </label>
                <Button type="submit" variant="primary" disabled={busy}>
                  {busy ? '연결 중…' : '계정 연결'}
                </Button>
              </form>
            )}
            <Button type="button" variant="outline"  => void createAccount()} disabled={busy}>
              새 DefectAgent 계정 만들기
            </Button>
            <p className="text-sm text-gray-500">계정 연결이 거부되면 관리자에게 문의해 주세요.</p>
            <a href={centralLogoutUrl()}  => useAuthStore.getState().clearSession()}
              className="text-sm text-primary-600">다른 Samsung 계정으로 로그인</a>
          </>
        ) : (
          <>
            {status === 'error' && <p role="alert">{statusError}</p>}
            <a href={centralLoginUrl()}
              className="px-4 py-2 rounded-lg bg-primary-600 text-white text-center font-medium">
              Samsung SSO로 로그인
            </a>
            {status === 'error' && (
              <Button type="button" variant="text"  => void useAuthStore.getState().bootstrap()}>
                로그인 상태 다시 확인
              </Button>
            )}

          </>
        )}
        {actionError && <p role="alert" className="text-sm text-red-600">{actionError}</p>}
      </div>
    </div>
  );
}
