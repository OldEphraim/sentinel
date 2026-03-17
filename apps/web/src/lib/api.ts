const API_BASE = process.env['NEXT_PUBLIC_API_URL'] ?? 'http://localhost:8000';

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

// Module-level demo key consumed by the next apiFetch call
let _pendingDemoKey: string | null = null;
export function setDemoKeyHeader(key: string): void {
  _pendingDemoKey = key;
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    ...(options?.headers as Record<string, string> | undefined),
  };

  if (typeof window !== 'undefined') {
    // Attach Bearer token if available
    try {
      const raw = localStorage.getItem('sentinel_auth');
      if (raw) {
        const parsed = JSON.parse(raw) as { token: string };
        headers['Authorization'] = `Bearer ${parsed.token}`;
      }
    } catch { /* ignore */ }

    // Attach demo key if pending
    if (_pendingDemoKey) {
      headers['X-Demo-Key'] = _pendingDemoKey;
      _pendingDemoKey = null;
    }
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (!res.ok) {
    const text = await res.text();
    throw new ApiError(res.status, `API error ${res.status}: ${text}`);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// --------------------------------------------------------------------------- //
// Auth endpoints
// --------------------------------------------------------------------------- //

export async function apiLogin(email: string, password: string) {
  return apiFetch<{ token: string; user: { id: string; email: string } }>('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
}

export async function apiSignup(email: string, password: string, demoKey: string) {
  return apiFetch<{ token: string; user: { id: string; email: string } }>('/api/auth/signup', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, demo_key: demoKey }),
  });
}

// --------------------------------------------------------------------------- //
// Watch / order endpoints
// --------------------------------------------------------------------------- //

export async function fetchWatches() {
  return apiFetch<unknown[]>('/api/watches/');
}

export async function fetchWatch(id: string) {
  return apiFetch<unknown>(`/api/watches/${id}`);
}

export async function fetchWatchOrders(watchId: string) {
  return apiFetch<unknown[]>(`/api/watches/${watchId}/orders`);
}

export async function createWatch(data: {
  name: string;
  question: string;
  aoi: object;
  sensor_preference: string;
  frequency: string;
  alert_threshold?: string;
}) {
  return apiFetch<unknown>('/api/watches/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

export async function deleteWatch(id: string) {
  return apiFetch<void>(`/api/watches/${id}`, { method: 'DELETE' });
}
