'use client';
import { useEffect, useState } from 'react';

const API_BASE = process.env['NEXT_PUBLIC_API_URL'] ?? 'http://localhost:8000';

export interface OrderUpdate {
  orderId: string;
  status: string;
  answer?: string;
  confidence?: string;
  evidence?: Array<{ type: string; description: string; value?: string | number }>;
  agentThoughts?: Array<{ step: number; toolCalled?: string; toolInput?: unknown; toolOutput?: unknown }>;
  updatedAt?: string;
}

export function useOrderStream(watchId: string): OrderUpdate[] {
  const [updates, setUpdates] = useState<OrderUpdate[]>([]);

  useEffect(() => {
    const source = new EventSource(`${API_BASE}/api/sse/watch/${watchId}/orders`);

    source.onmessage = (e: MessageEvent<string>) => {
      try {
        const data = JSON.parse(e.data) as OrderUpdate;
        if (!data.orderId) return;
        setUpdates((prev) => {
          const idx = prev.findIndex((u) => u.orderId === data.orderId);
          if (idx >= 0) {
            const next = [...prev];
            next[idx] = data;
            return next;
          }
          return [data, ...prev];
        });
      } catch {
        // ignore parse errors
      }
    };

    source.onerror = () => {
      console.warn('[useOrderStream] SSE connection dropped, will auto-reconnect...');
    };

    return () => source.close();
  }, [watchId]);

  return updates;
}
