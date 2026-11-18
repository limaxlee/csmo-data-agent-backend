export const threadKeys = {
  all: ['threads'] as const,
  list: () => [...threadKeys.all, 'list'] as const,
  conversation: (threadId: string) => [...threadKeys.all, threadId, 'conversation'] as const,
};

export const trainDataKeys = {
  all: ['train-data'] as const,
  list: (threadId: string) => [...trainDataKeys.all, threadId] as const,
};

// Not under trainDataKeys.all: the upload, delete and register-mask hooks invalidate
// that whole prefix, which would request every image on screen again.
export const trainDataFileKeys = {
  all: ['train-data-file'] as const,
  blob: (threadId: string, fileId: string) => [...trainDataFileKeys.all, threadId, fileId] as const,
  thumbnail: (threadId: string, fileId: string) =>
    [...trainDataFileKeys.all, threadId, fileId, 'thumbnail'] as const,
  maskOverlay: (threadId: string, maskFileId: string) =>
    [...trainDataFileKeys.all, threadId, maskFileId, 'overlay'] as const,
};

export const resultKeys = {
  all: ['results'] as const,
  list: (threadId: string) => [...resultKeys.all, threadId] as const,
  // A separate root, like trainDataFileKeys: invalidating the list must not pull
  // every image on screen down again.
  blob: (threadId: string, planId: string, filename: string) =>
    ['result-file', threadId, planId, filename] as const,
  maskBlob: (threadId: string, planId: string, filename: string) =>
    [...resultKeys.blob(threadId, planId, filename), 'mask'] as const,
  maskOverlay: (threadId: string, planId: string, filename: string) =>
    [...resultKeys.blob(threadId, planId, filename), 'mask', 'overlay'] as const,
};

export const authKeys = {
  me: () => ['auth', 'me'] as const,
};
