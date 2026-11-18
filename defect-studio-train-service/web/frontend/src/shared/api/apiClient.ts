// The single ApiClient instance shared across the app. Importing this
// (rather than constructing a new client per call site) means a token set once
// — supplied by the active auth mode — is visible to every request and stream.
import { ApiClient } from '@defect-studio/api-client';

export const apiClient = new ApiClient();

