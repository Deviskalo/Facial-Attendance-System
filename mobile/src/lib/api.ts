export type MobileUser = {
  id: number;
  username: string;
  display_name: string;
  role: 'admin' | 'operator' | 'reviewer';
};

export type DashboardData = {
  date: string;
  metrics: {
    enrolled: number;
    present: number;
    late: number;
    absent: number;
  };
  classes: Array<{
    class_name: string;
    enrolled: number;
    present: number;
    late: number;
    absent: number;
  }>;
};

export type Person = {
  id: string;
  name: string;
  department: string;
  role: string;
  is_active: boolean;
  created_at: string;
  classes: Array<{ id: number; name: string }>;
};

export type AttendanceRecord = {
  id: number;
  employee_id: string;
  name: string;
  department: string;
  role: string;
  timestamp: string;
  event_type: string;
  status: string;
};

export type Page<T> = {
  items: T[];
  total: number;
  limit: number;
  offset: number;
};

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export function normalizeApiBaseUrl(value: string): string {
  let url: URL;
  try {
    url = new URL(value.trim());
  } catch {
    throw new ApiError('Enter the full HTTPS address of your attendance server.');
  }

  if (
    url.protocol !== 'https:' ||
    !url.hostname ||
    url.username ||
    url.password ||
    url.search ||
    url.hash
  ) {
    throw new ApiError(
      'For security, the server address must use HTTPS and cannot include credentials or query parameters.',
    );
  }

  return `${url.origin}${url.pathname.replace(/\/+$/, '')}`;
}

export async function fetchJson<T>(
  baseUrl: string,
  path: string,
  token?: string,
  init?: RequestInit,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${baseUrl}${path}`, {
      ...init,
      headers: {
        Accept: 'application/json',
        ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...init?.headers,
      },
    });
  } catch {
    throw new ApiError(
      'Could not reach the server. Check the HTTPS address and network connection.',
    );
  }

  const payload = (await response.json().catch(() => null)) as
    | { detail?: unknown }
    | null;
  if (!response.ok) {
    const message =
      typeof payload?.detail === 'string'
        ? payload.detail
        : `The server returned an error (${response.status}).`;
    throw new ApiError(message, response.status);
  }
  if (payload === null) {
    throw new ApiError('The server returned an invalid response.');
  }
  return payload as T;
}
