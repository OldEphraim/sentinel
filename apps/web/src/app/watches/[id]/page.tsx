'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import dynamic from 'next/dynamic';
import { ChevronDown, ChevronRight, Loader2, CheckCircle2, XCircle, Clock } from 'lucide-react';
import { fetchWatch, fetchWatchOrders } from '@/lib/api';
import { useOrderStream } from '@/hooks/useOrderStream';
import { formatDate, SENSOR_ICONS, statusColor, statusBg, STATUS_LABELS } from '@/lib/utils';
import AuthGuard from '@/components/AuthGuard';

const AoiMap = dynamic(() => import('@/components/AoiMap'), { ssr: false });

function StatusIcon({ status }: { status: string }) {
  if (['processing', 'interpreting', 'pending'].includes(status)) {
    return <Loader2 className="w-4 h-4 animate-spin text-blue-400" />;
  }
  if (status === 'answered' || status === 'complete') {
    return <CheckCircle2 className="w-4 h-4 text-emerald-400" />;
  }
  if (status === 'failed') {
    return <XCircle className="w-4 h-4 text-red-400" />;
  }
  return <Clock className="w-4 h-4 text-slate-400" />;
}

function OrderCard({ order }: { order: Record<string, unknown> }) {
  const [expanded, setExpanded] = useState(false);
  const status = order['status'] as string;
  const thoughts = order['agentThoughts'] as unknown[] | undefined;

  return (
    <div className={`rounded-xl border p-5 ${statusBg(status)}`}>
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2">
          <StatusIcon status={status} />
          <span className={`text-sm font-medium ${statusColor(status)}`}>
            {STATUS_LABELS[status] ?? status}
          </span>
          {(order['sensorType'] as string | undefined) && (
            <span className="text-slate-500 text-xs">
              {SENSOR_ICONS[order['sensorType'] as string] ?? ''} {order['sensorType'] as string}
            </span>
          )}
          {(order['analyticsType'] as string | undefined) && (
            <span className="text-slate-500 text-xs">• {order['analyticsType'] as string}</span>
          )}
        </div>
        <span className="text-xs text-slate-500">
          {formatDate((order['updatedAt'] as string | undefined) ?? (order['createdAt'] as string))}
        </span>
      </div>

      {/* Answer */}
      {(order['answer'] as string | undefined) && (
        <div className="bg-slate-900/60 rounded-lg p-4 mb-3">
          <p className="text-sm text-slate-100 leading-relaxed">{order['answer'] as string}</p>
          {(order['confidence'] as string | undefined) && (
            <p className="text-xs text-slate-500 mt-2">
              Confidence: <span className="capitalize">{order['confidence'] as string}</span>
            </p>
          )}
        </div>
      )}

      {/* Evidence */}
      {Array.isArray(order['evidence']) && order['evidence'].length > 0 && (
        <ul className="space-y-1 mb-3">
          {(order['evidence'] as Array<Record<string, unknown>>).map((item, i) => (
            <li key={i} className="text-xs text-slate-400 flex items-start gap-2">
              <span className="text-slate-600 mt-0.5">•</span>
              <span>{item['description'] as string}{item['value'] !== undefined ? `: ${String(item['value'])}` : ''}</span>
            </li>
          ))}
        </ul>
      )}

      {/* Agent reasoning (collapsible) */}
      {thoughts && thoughts.length > 0 && (
        <div>
          <button
            type="button"
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300 transition-colors"
          >
            {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            Agent reasoning ({thoughts.length} steps)
          </button>
          {expanded && (
            <div className="mt-2 space-y-2">
              {(thoughts as Array<Record<string, unknown>>).map((t, i) => (
                <div key={i} className="bg-slate-900/40 rounded p-3 text-xs font-mono">
                  <div className="text-slate-400 mb-1">
                    Step {(t['step'] as number) + 1}: <span className="text-blue-400">{t['toolCalled'] as string}</span>
                  </div>
                  {(t['toolInput'] as Record<string, unknown> | undefined) && (
                    <pre className="text-slate-500 overflow-x-auto text-xs">
                      {JSON.stringify(t['toolInput'], null, 2)}
                    </pre>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function WatchDetail() {
  const params = useParams<{ id: string }>();
  const watchId = params.id;
  const [watch, setWatch] = useState<Record<string, unknown> | null>(null);
  const [orders, setOrders] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);
  const [elapsed, setElapsed] = useState(0);

  const streamUpdates = useOrderStream(watchId);

  // Merge SSE updates into orders list
  useEffect(() => {
    if (streamUpdates.length === 0) return;
    setOrders((prev) => {
      const merged = [...prev];
      for (const update of streamUpdates) {
        const idx = merged.findIndex((o) => o['id'] === update.orderId);
        if (idx >= 0) {
          merged[idx] = { ...merged[idx], ...update, id: update.orderId };
        }
      }
      return [...merged];
    });
  }, [streamUpdates]);

  // Polling fallback — every 5s in case SSE drops before the update arrives
  useEffect(() => {
    const id = setInterval(async () => {
      try {
        const o = await fetchWatchOrders(watchId) as Record<string, unknown>[];
        setOrders(o);
      } catch {
        // ignore fetch errors — SSE or next poll will catch up
      }
    }, 5000);
    return () => clearInterval(id);
  }, [watchId]);

  // Elapsed time counter — only active when there are no orders yet
  useEffect(() => {
    if (orders.length > 0) return;
    const id = setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => clearInterval(id);
  }, [orders.length]);

  useEffect(() => {
    const load = async () => {
      try {
        const [w, o] = await Promise.all([
          fetchWatch(watchId) as Promise<Record<string, unknown>>,
          fetchWatchOrders(watchId) as Promise<Record<string, unknown>[]>,
        ]);
        setWatch(w);
        setOrders(o);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [watchId]);

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-12 bg-slate-800 rounded-xl animate-pulse w-1/2" />
        <div className="h-64 bg-slate-800 rounded-xl animate-pulse" />
      </div>
    );
  }

  if (!watch) {
    return <div className="text-slate-400">Watch not found.</div>;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <span className="text-2xl">{SENSOR_ICONS[watch['sensor_preference'] as string] ?? '🛰️'}</span>
          <h1 className="text-2xl font-semibold">{watch['name'] as string}</h1>
        </div>
        <p className="text-slate-400">{watch['question'] as string}</p>
        <p className="text-xs text-slate-600 mt-1">
          Created {formatDate(watch['created_at'] as string)} •{' '}
          {watch['frequency'] as string}
        </p>
      </div>

      {/* Map */}
      <div className="h-48 rounded-xl overflow-hidden border border-slate-700">
        <AoiMap
          value={watch['aoi'] as { type: 'Polygon'; coordinates: number[][][] } | null}
          onChange={() => {}}
          readOnly
        />
      </div>

      {/* Orders timeline */}
      <div>
        <h2 className="text-lg font-medium mb-3">Order History</h2>
        {orders.length === 0 ? (
          <div className="text-sm">
            <div className="flex items-center gap-2 text-slate-500">
              <Loader2 className="w-4 h-4 animate-spin" />
              Running agent...{elapsed >= 5 && <span>({elapsed}s)</span>}
            </div>
            {elapsed >= 30 && elapsed < 60 && (
              <p className="text-xs text-slate-600 mt-1 ml-6">
                Selecting optimal satellite &amp; analytics configuration
              </p>
            )}
            {elapsed >= 60 && (
              <p className="text-xs text-slate-600 mt-1 ml-6">
                This can take up to 2 minutes for complex queries
              </p>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            {orders.map((order) => (
              <OrderCard key={order['id'] as string} order={order} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function WatchDetailPage() {
  return (
    <AuthGuard>
      <WatchDetail />
    </AuthGuard>
  );
}
