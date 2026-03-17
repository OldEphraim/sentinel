'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Clock } from 'lucide-react';
import { fetchWatches, deleteWatch } from '@/lib/api';
import { formatDate, SENSOR_ICONS, statusBg } from '@/lib/utils';
import AuthGuard from '@/components/AuthGuard';

function WatchList() {
  const [watches, setWatches] = useState<unknown[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      const data = await fetchWatches();
      setWatches(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    const interval = setInterval(() => void load(), 10_000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-28 rounded-xl bg-slate-800 animate-pulse" />
        ))}
      </div>
    );
  }

  if (watches.length === 0) {
    return (
      <div className="text-center py-24">
        <div className="text-6xl mb-4">🛰️</div>
        <h2 className="text-2xl font-semibold mb-2">No watches yet</h2>
        <p className="text-slate-400 mb-8">
          Create a watch to start asking questions about any location on Earth.
        </p>
        <Link
          href="/watches/new"
          className="bg-blue-600 hover:bg-blue-500 text-white px-6 py-3 rounded-lg font-medium transition-colors"
        >
          Create your first watch
        </Link>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-6">Active Watches</h1>
      <div className="space-y-3">
        {(watches as Record<string, unknown>[]).map((watch) => (
          <div key={watch['id'] as string} className={`rounded-xl border p-5 hover:border-slate-500 transition-colors ${statusBg('active')}`}>
            <div className="flex items-start gap-4">
              <Link
                href={`/watches/${watch['id'] as string}`}
                className="flex-1 min-w-0 cursor-pointer"
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-lg">
                    {SENSOR_ICONS[watch['sensor_preference'] as string] ?? '🛰️'}
                  </span>
                  <h3 className="font-medium truncate">{watch['name'] as string}</h3>
                </div>
                <p className="text-slate-400 text-sm line-clamp-2">{watch['question'] as string}</p>
              </Link>
              <div className="flex flex-col items-end gap-2 shrink-0">
                <div className="flex flex-col items-end gap-1">
                  <span className="text-xs text-slate-500 flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {formatDate(watch['created_at'] as string)}
                  </span>
                  <span className="text-xs capitalize text-slate-400">
                    {watch['frequency'] as string}
                  </span>
                </div>
                <button
                  type="button"
                  className="text-xs text-slate-500 hover:text-red-400 hover:bg-red-950/50 px-2 py-1 rounded transition-colors"
                  onClick={async (e) => {
                    e.stopPropagation();
                    e.preventDefault();
                    if (!window.confirm('Delete this watch and all its orders?')) return;
                    await deleteWatch(watch['id'] as string);
                    setWatches((prev) => (prev as Record<string, unknown>[]).filter((w) => w['id'] !== watch['id']));
                  }}
                >
                  Delete
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function HomePage() {
  return (
    <AuthGuard>
      <WatchList />
    </AuthGuard>
  );
}
