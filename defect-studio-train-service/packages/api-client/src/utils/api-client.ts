// Shared transport for every backend call. The app may supply a token provider
// so requests and event streams can refresh their bearer before sending.

import { ApiError } from './api-error';
import type { AgentEvent } from './events.dto';
import { openAgentStream } from './open-agent-stream';

interface RuntimeImportMetaEnv {
  VITE_AGENT_API_URL?: string;
}

const getDefaultBaseUrl = (): string => {
  const url = (import.meta as ImportMeta & { env?: RuntimeImportMetaEnv }).env?.VITE_AGENT_API_URL;
  if (url) return url;
  if (typeof window !== 'undefined' && window.location.hostname) {
    return `http://${window.location.hostname}:8080`;
  }
  return 'http://localhost:8080';
};

export interface ApiClientOptions {
  baseUrl?: string;
  token?: string | null;
}

export type TokenProvider = (forceRefresh?: boolean) => Promise<string | null>;

export class ApiClient {
  private readonly baseUrl: string;
  private token: string | null;
  private tokenProvider: TokenProvider | null = null;

  // Called only when a rejected token cannot be refreshed.
  onUnauthorized: (() => void) | null = null;

  constructor({ baseUrl, token }: ApiClientOptions = {}) {
    this.baseUrl = baseUrl ?? getDefaultBaseUrl();
    this.token = token ?? null;
  }

  setToken(token: string | null): void {
    this.token = token;
  }

  getToken(): string | null {
    return this.token;
  }

  setTokenProvider(provider: TokenProvider | null): void {
    this.tokenProvider = provider;
  }

  private async bearer(forceRefresh = false): Promise<string> {
    const token = this.tokenProvider ? await this.tokenProvider(forceRefresh) : this.token;
    if (!token) throw new Error('Not authenticated: no access token set');
    return token;
  }

  // Adds the token when `auth`, sets the JSON Content-Type unless the body is
  // FormData, and throws ApiError on any non-2xx.
  private async send(path: string, init: RequestInit, auth: boolean): Promise<Response> {
    const headers = new Headers(init.headers);
    if (auth) headers.set('Authorization', `Bearer ${await this.bearer()}`);
    if (init.body !== undefined && !(init.body instanceof FormData) && !headers.has('Content-Type')) {
      const tag = Object.prototype.toString.call(init.body);
      if (init.body instanceof Blob || tag === '[object Blob]') {
        const mime = (init.body as Blob).type;
        if (mime) headers.set('Content-Type', mime);
      } else if (
        !(init.body instanceof ArrayBuffer) &&
        tag !== '[object ArrayBuffer]' &&
        !ArrayBuffer.isView(init.body)
      ) {
        headers.set('Content-Type', 'application/json');
      }
    }
    let response = await fetch(`${this.baseUrl}${path}`, { ...init, headers });
    let retried = false;
    if (auth && response.status === 401 && this.tokenProvider) {
      const token = await this.bearer(true);
      if (['GET', 'HEAD'].includes((init.method ?? 'GET').toUpperCase())) {
        headers.set('Authorization', `Bearer ${token}`);
        response = await fetch(`${this.baseUrl}${path}`, { ...init, headers });
        retried = true;
      }
    }
    if (!response.ok) {
      if (auth && response.status === 401 && (!this.tokenProvider || retried)) {
        this.onUnauthorized?.();
      }
      throw new ApiError(response.status, response.statusText, await response.text());
    }
    return response;
  }

  // Decodes the response as JSON. Returns undefined for 204.
  async request<T>(path: string, init: RequestInit = {}, auth = true): Promise<T> {
    const response = await this.send(path, init, auth);
    if (response.status === 204) return undefined as T;
    return (await response.json()) as T;
  }

  // Reads the response as raw bytes, for endpoints that return an image rather
  // than JSON.
  async requestBlob(path: string): Promise<Blob> {
    const response = await this.send(path, { method: 'GET' }, true);
    return response.blob();
  }

  // Opens a server-sent-events stream. Uses fetch because EventSource cannot send
  // the token.
  async *openStream(path: string, signal?: AbortSignal): AsyncGenerator<AgentEvent> {
    const url = `${this.baseUrl}${path}`;
    try {
      yield* openAgentStream({ url, token: await this.bearer(), signal });
    } catch (error) {
      if (!(error instanceof ApiError) || error.status !== 401 || !this.tokenProvider) {
        if (error instanceof ApiError && error.status === 401) this.onUnauthorized?.();
        throw error;
      }
      try {
        yield* openAgentStream({ url, token: await this.bearer(true), signal });
      } catch (retryError) {
        if (retryError instanceof ApiError && retryError.status === 401) this.onUnauthorized?.();
        throw retryError;
      }
    }
  }
}

