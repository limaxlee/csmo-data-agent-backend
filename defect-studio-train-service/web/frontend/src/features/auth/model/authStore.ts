import { create } from 'zustand';
import { ApiClient, ApiError, getMe, provisionSso, type User } from '@defect-studio/api-client';
import { apiClient } from '@/shared/api/apiClient';
import { queryClient } from '@/shared/api/queryClient';
import { useActiveThreadStore } from '@/features/threads/model/activeThreadStore';
import { useAgentStore } from '@/features/agent-run/model/agentStore';
import { CentralAuthError, getCentralSession, getCentralToken } from './centralAuth';
import { clearSsoRedirectAttempt } from './ssoRedirect';

const STORAGE_KEY = 'defect-studio-auth';
const SSO_OWNER_KEY = 'defect-studio-sso-owner'; // Identity marker only; never a bearer.
const REFRESH_MARGIN_SECONDS = 60;
const unauthenticated = { token: null, expiresAt: null, user: null, mode: null } as const;

export type AuthStatus = 'loading' | 'signed-out' | 'unlinked' | 'authenticated' | 'error';
export type AuthMode = 'sso';

interface AuthState {
  status: AuthStatus;
  mode: AuthMode | null;
  token: string | null;
  expiresAt: number | null;
  user: User | null;
  error: string | null;
  setSsoUser: (user: User) => void;
  clearSession: () => void;
  bootstrap: () => Promise<void>;
  getBearer: (forceRefresh?: boolean) => Promise<string | null>;
}

// SSO is restored from web-auth's HttpOnly cookie. Discard old password tokens.
function clearLegacyTokens(): void {
  localStorage.removeItem(STORAGE_KEY);
  sessionStorage.removeItem(STORAGE_KEY);
}

function clearPrivateData(): void {
  queryClient.clear();
  useAgentStore.getState().resetSession();
  useActiveThreadStore.getState().setActiveThreadId(null);
}

function errorCode(error: unknown): string | null {
  if (!(error instanceof ApiError)) return null;
  try {
    return (JSON.parse(error.body) as { code?: string }).code ?? null;
  } catch {
    return null;
  }
}

let refreshRequest: Promise<string> | null = null;
let authGeneration = 0;

async function resolveSsoUser(client: ApiClient): Promise<User> {
  try {
    return await getMe(client);
  } catch (error) {
    if (import.meta.env.VITE_DEPLOYMENT_ENV === 'production' && errorCode(error) === 'sso_account_unlinked') {
      return provisionSso(client);
    }
    throw error;
  }
}

export const useAuthStore = create<AuthState>((set, get) => ({
  status: 'loading',
  ...unauthenticated,
  error: null,

  setSsoUser: (user) => {
    clearSsoRedirectAttempt();
    const previous = get();
    if (previous.user?.id !== user.id || previous.mode !== 'sso') clearPrivateData();
    localStorage.setItem(SSO_OWNER_KEY, user.id);
    clearLegacyTokens();
    set({ status: 'authenticated', mode: 'sso', user, error: null });
  },

  clearSession: () => {
    authGeneration++;
    refreshRequest = null;
    apiClient.setTokenProvider(null);
    apiClient.setToken(null);
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(SSO_OWNER_KEY);
    clearLegacyTokens();
    set({ status: 'signed-out', ...unauthenticated, error: null });
    clearPrivateData();
  },

  bootstrap: async () => {
    const restoreThread = useActiveThreadStore.getState().activeThreadId;
    const restoreOwner = localStorage.getItem(SSO_OWNER_KEY);
    const generation = ++authGeneration;
    refreshRequest = null;
    clearLegacyTokens();
    set({ status: 'loading', ...unauthenticated, error: null });
    clearPrivateData();
    apiClient.setTokenProvider(null);
    apiClient.setToken(null);
    try {
      const session = await getCentralSession();
      if (generation !== authGeneration) return;
      if (!session.authenticated) {
        set({ status: 'signed-out' });
        return;
      }
      const service = await getCentralToken();
      if (generation !== authGeneration) return;
      apiClient.setToken(service.accessToken);
      apiClient.setTokenProvider((force) => useAuthStore.getState().getBearer(force));
      set({ mode: 'sso', token: service.accessToken, expiresAt: service.expiresAt });
      const user = await resolveSsoUser(apiClient);
      if (generation !== authGeneration) return;
      get().setSsoUser(user);
      // Restore navigation only after the backend verified the same SSO user.
      // Dataset/Thread permissions are still checked by their normal API reads.
      if (restoreThread && restoreOwner === user.id) {
        useActiveThreadStore.getState().setActiveThreadId(restoreThread);
      }
    } catch (error) {
      if (generation !== authGeneration) return;
      if (errorCode(error) === 'sso_account_unlinked') {
        set({ status: 'unlinked', error: null });
      } else if ((error instanceof CentralAuthError || error instanceof ApiError) && error.status === 401) {
        get().clearSession();
      } else {
        set({ status: 'error', error: '로그인 상태를 확인하지 못했습니다. 다시 시도해 주세요.' });
      }
    }
  },

  getBearer: async (forceRefresh = false) => {
    const state = get();
    if (state.mode === null) return apiClient.getToken();
    const stale = state.mode === 'sso'
      && (state.expiresAt === null || state.expiresAt <= Date.now() / 1000 + REFRESH_MARGIN_SECONDS);
    if (!forceRefresh && !stale && state.token) return state.token;
    if (!refreshRequest) {
      const generation = authGeneration;
      const pending = (async () => {
        if (get().mode === 'sso') {
          const service = await getCentralToken();
          if (generation !== authGeneration) throw new Error('Authentication changed');
          // A central session may have switched accounts in another tab. Resolve
          // the new bearer before any waiting request can use it with old data.
          if (get().status === 'authenticated') {
            let renewedUser: User;
            try {
              renewedUser = await resolveSsoUser(new ApiClient({ token: service.accessToken }));
            } catch (error) {
              if (errorCode(error) === 'sso_account_unlinked') {
                if (generation !== authGeneration) throw error;
                set({
                  status: 'unlinked', mode: 'sso', token: service.accessToken,
                  expiresAt: service.expiresAt, user: null,
                });
                apiClient.setToken(service.accessToken);
                clearPrivateData();
                throw error;
              }
              throw error;
            }
            if (generation !== authGeneration) throw new Error('Authentication changed');
            if (renewedUser.id !== get().user?.id) {
              set({ token: service.accessToken, expiresAt: service.expiresAt });
              apiClient.setToken(service.accessToken);
              get().setSsoUser(renewedUser);
              throw new Error('Authentication changed');
            }
            set({ user: renewedUser });
          }
          set({ token: service.accessToken, expiresAt: service.expiresAt });
          apiClient.setToken(service.accessToken);
          return service.accessToken;
        }
        throw new Error('No SSO session');
      })();
      const shared = pending.finally(() => {
        if (refreshRequest === shared) refreshRequest = null;
      });
      refreshRequest = shared;
    }
    try {
      return await refreshRequest;
    } catch (error) {
      if ((error instanceof CentralAuthError && error.status === 401)
        || (error instanceof ApiError && error.status === 401)) get().clearSession();
      throw error;
    }
  },
}));

apiClient. => {
  useAuthStore.getState().clearSession();
};

