import { useQuery } from '@tanstack/react-query';
import { getTrainDataFileThumbnail } from '@defect-studio/api-client';
import { apiClient } from '@/shared/api/apiClient';
import { trainDataFileKeys } from '@/shared/api/keys';

// The thumbnail bytes of one uploaded file. A thumbnail is a 256px JPEG generated
// server-side. The request is never sent again while the result is kept. React Query
// deletes the result 10 minutes after the last component using it unmounts.
export function useTrainDataFileThumbnail(threadId: string | null, fileId: string | null | undefined) {
  return useQuery({
    queryKey: trainDataFileKeys.thumbnail(threadId ?? '', fileId ?? ''),
    queryFn: () => getTrainDataFileThumbnail(apiClient, threadId ?? '', fileId ?? ''),
    enabled: Boolean(threadId && fileId),
    staleTime: Infinity,
    gcTime: 10 * 60 * 1000,
  });
}

