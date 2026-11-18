import { useQuery } from '@tanstack/react-query';
import { getTrainDataFile } from '@defect-studio/api-client';
import { apiClient } from '@/shared/api/apiClient';
import { trainDataFileKeys } from '@/shared/api/keys';

// The bytes of one uploaded file. A file id always refers to the same bytes, so the
// request is never sent again while the result is kept. React Query deletes the result
// 10 minutes after the last component using it unmounts.
export function useTrainDataFileBlob(threadId: string | null, fileId: string | null | undefined) {
  return useQuery({
    queryKey: trainDataFileKeys.blob(threadId ?? '', fileId ?? ''),
    queryFn: () => getTrainDataFile(apiClient, threadId ?? '', fileId ?? ''),
    enabled: Boolean(threadId && fileId),
    staleTime: Infinity,
    gcTime: 10 * 60 * 1000,
  });
}
