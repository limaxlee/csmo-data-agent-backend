import ReactDOM from 'react-dom/client';
import App from './App';
import { Providers } from './Providers';
import { useAuthStore } from '@/features/auth/model/authStore';
import './index.css';

// Mock APIs are available only in the explicit development mock profile.
async function enableMocking() {
  if (!import.meta.env.DEV || import.meta.env.MODE !== 'mock') return;
  const { worker } = await import('@/mocks/browser');
  return worker.start({
    onUnhandledRequest: (request, print) => {
      const url = new URL(request.url);
      if (/^\/api(?:\/|$)/.test(url.pathname) || /^\/mock(?:\/|$)/.test(url.pathname)) {
        print.warning();
      }
    },
  });
}

enableMocking().then(() => {
  const root = document.getElementById('root');
  if (root) {
    ReactDOM.createRoot(root).render(
      <Providers>
        <App />
      </Providers>,
    );
  }
  void useAuthStore.getState().bootstrap();
});