import { useEffect } from 'react';
import { useAppStore } from '@/shared/model/appStore';
import { TabNav } from '@/widgets/TabNav';
import { UploadTab } from '@/pages/UploadTab';
import { BackgroundTab } from '@/pages/BackgroundTab';
import { GalleryTab } from '@/pages/GalleryTab';
import { AgentTab } from '@/pages/AgentTab';
import { ThreadSidebar } from '@/features/threads/ui/ThreadSidebar';
import { LoginScreen } from '@/features/auth/ui/LoginScreen';
import { useAuthStore } from '@/features/auth/model/authStore';
import { useShowActiveThread } from '@/features/agent-run/model/useShowActiveThread';
import { UploadProgressPanel } from '@/features/train-data/ui/UploadProgressPanel';

function App() {
  const store = useAppStore();
  const status = useAuthStore((s) => s.status);

  useEffect(() => {
    if (store.darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [store.darkMode]);

  if (status === 'loading') {
    return <div role="status" className="min-h-screen flex items-center justify-center">로그인 상태 확인 중…</div>;
  }

  if (status !== 'authenticated') {
    return <LoginScreen />;
  }

  return <AuthenticatedApp activeTab={store.activeTab} />;
}

function AuthenticatedApp({ activeTab }: { activeTab: ReturnType<typeof useAppStore.getState>['activeTab'] }) {
  useShowActiveThread();

  return (
    <div className="h-screen flex overflow-hidden bg-gray-50 dark:bg-dark-300 text-gray-900 dark:text-gray-100 transition-colors">
      <ThreadSidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <TabNav />
        {/* Every tab manages its own internal scroll regions within the fixed viewport height. */}
        <main className="flex-1 min-h-0 overflow-hidden bg-white dark:bg-dark-300">
          <div className="max-w-[1800px] w-full h-full min-h-0 mx-auto px-4 py-4 flex flex-col">
            {activeTab === 'agent' && <AgentTab />}
            {activeTab === 'upload' && <UploadTab />}
            {activeTab === 'background' && <BackgroundTab />}
            {activeTab === 'gallery' && <GalleryTab />}
          </div>
        </main>
        <footer className="border-t border-gray-200 dark:border-gray-800 bg-white/50 dark:bg-dark-200/50">
          <div className="max-w-[1800px] mx-auto px-4 py-2 text-center text-xs text-gray-500 dark:text-gray-400">
            DefectAgent v1.0
          </div>
        </footer>
      </div>
      <UploadProgressPanel />
    </div>
  );
}

export default App;
