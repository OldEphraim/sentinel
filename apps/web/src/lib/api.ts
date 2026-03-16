const API_BASE = process.env['NEXT_PUBLIC_API_URL'] ?? 'http://localhost:8000';

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, options);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

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
