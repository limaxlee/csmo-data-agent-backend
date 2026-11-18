import { Bot, ScanSearch, Image, LogOut, Moon, Sparkles, Sun, type LucideIcon } from 'lucide-react';
import { IconButton } from '@defect-studio/ui';
import { useAppStore } from '@/shared/model/appStore';
import { useAuthStore } from '@/features/auth/model/authStore';
import { centralLogoutUrl } from '@/features/auth/model/centralAuth';
import { markSsoRedirectAttempt } from '@/features/auth/model/ssoRedirect';

const tabs = [
  { id: 'agent' as const, label: '에이전트', icon: Bot },
  { id: 'upload' as const, label: '불량 이미지', icon: ScanSearch },
  { id: 'background' as const, label: '정상 이미지', icon: Image },
  { id: 'gallery' as const, label: '생성 이미지', icon: Sparkles },
];

interface TabButtonProps {
  icon: LucideIcon;
  label: string;
  active: boolean;
  onClick: () => void;
}

function TabButton({ icon: Icon, label, active, onClick }: TabButtonProps) {
  const textTone = active
    ? 'text-primary-600 dark:text-primary-400'
    : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300';

  return (
    <button
      
      className={`relative flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors ${textTone}`}
    >
      <Icon size={16} />{label}
      {active && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary-500" />}
    </button>
  );
}

export function TabNav() {
  const store = useAppStore();
  const mode = useAuthStore((s) => s.mode);
  const clearSession = useAuthStore((s) => s.clearSession);
  const modeLabel = store.darkMode ? '라이트 모드' : '다크 모드';

  return (
    <div className="border-b border-gray-200 dark:border-gray-800 bg-white/50 dark:bg-dark-200/30">
      <div className="max-w-[1800px] mx-auto px-4">
        <nav className="flex gap-1">
          {tabs.map((tab) => (
            <TabButton
              key={tab.id}
              icon={tab.icon}
              label={tab.label}
              active={store.activeTab === tab.id}
               => store.setActiveTab(tab.id)}
            />
          ))}
          <div className="ml-auto flex shrink-0 items-center gap-1">
            <IconButton
              type="button"
               => store.setDarkMode(!store.darkMode)}
              aria-label={modeLabel}
              title={modeLabel}
            >
              {store.darkMode ? <Sun size={16} aria-hidden="true" /> : <Moon size={16} aria-hidden="true" />}
            </IconButton>
            {mode === 'sso' ? (
              <a
                href={centralLogoutUrl()}
                 => { markSsoRedirectAttempt(); clearSession(); }}
                aria-label="로그아웃"
                title="로그아웃"
                className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-gray-500 transition-colors hover:bg-gray-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 dark:text-gray-400 dark:hover:bg-dark-100"
              >
                <LogOut size={16} aria-hidden="true" />
              </a>
            ) : (
              <IconButton type="button"  aria-label="로그아웃" title="로그아웃">
                <LogOut size={16} aria-hidden="true" />
              </IconButton>
            )}
          </div>
        </nav>
      </div>
    </div>
  );
}
