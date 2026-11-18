import type { ReactNode } from 'react';
import { QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import { queryClient } from '@/shared/api/queryClient';

export function Providers({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <Toaster position="top-right" toastOptions={{
        className: 'dark:bg-dark-100 dark:text-white',
        duration: 3000,
      }} />
    </QueryClientProvider>
  );
}
