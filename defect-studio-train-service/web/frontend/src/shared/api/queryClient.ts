import { QueryClient } from '@tanstack/react-query';

const MINUTE = 60 * 1000;

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
      refetchOnWindowFocus: false,
      staleTime: 30 * 1000,
      gcTime: 30 * MINUTE,
    },
  },
});