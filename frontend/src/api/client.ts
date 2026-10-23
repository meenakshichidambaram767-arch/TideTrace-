export class ApiError extends Error {
  code: string;
  statusCode: number;
  details?: any;
  requestId?: string;

  constructor(statusCode: number, code: string, message: string, details?: any, requestId?: string) {
    super(message);
    this.name = 'ApiError';
    this.statusCode = statusCode;
    this.code = code;
    this.details = details;
    this.requestId = requestId;
  }
}

const BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

export async function apiClient<T>(
  endpoint: string,
  options: RequestInit & {
    customHeaders?: Record<string, string>;
  } = {}
): Promise<T> {
  const token = localStorage.getItem('tidetrace_token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.customHeaders || {}),
  };

  const url = endpoint.startsWith('http') ? endpoint : `${BASE_URL}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (response.status === 204) {
      return {} as T;
    }

    const data = await response.json().catch(() => null);

    if (!response.ok) {
      if (data && data.error) {
        throw new ApiError(
          response.status,
          data.error.code || 'API_ERROR',
          data.error.message || `Request failed with status ${response.status}`,
          data.error.details,
          data.error.request_id
        );
      }
      throw new ApiError(
        response.status,
        `HTTP_${response.status}`,
        data?.detail || response.statusText || 'Unknown network error'
      );
    }

    return data as T;
  } catch (err: any) {
    if (err instanceof ApiError) {
      throw err;
    }
    throw new ApiError(0, 'NETWORK_ERROR', err.message || 'Failed to connect to the TideTrace API server');
  }
}
