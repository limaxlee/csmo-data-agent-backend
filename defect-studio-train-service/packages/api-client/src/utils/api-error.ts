// Thrown by ApiClient for any non-2xx response from the BFF.
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly statusText: string,
    readonly body: string,
    readonly retryAfter: string | null = null,
  ) {
    super(`Agent request failed: ${status} ${statusText}`);
    this.name = 'ApiError';
  }
}
