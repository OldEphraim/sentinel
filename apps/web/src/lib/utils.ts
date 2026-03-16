import { clsx, type ClassValue } from 'clsx';

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export const SENSOR_ICONS: Record<string, string> = {
  optical: '🌤',
  sar: '📡',
  free: '🌍',
};

export const STATUS_LABELS: Record<string, string> = {
  pending: 'Pending',
  processing: 'Processing',
  interpreting: 'Interpreting',
  answered: 'Answered',
  complete: 'Complete',
  failed: 'Failed',
};

export function statusColor(status: string): string {
  const colors: Record<string, string> = {
    pending: 'text-slate-400',
    processing: 'text-blue-400',
    interpreting: 'text-violet-400',
    answered: 'text-emerald-400',
    complete: 'text-emerald-400',
    failed: 'text-red-400',
  };
  return colors[status] ?? 'text-slate-400';
}

export function statusBg(status: string): string {
  const colors: Record<string, string> = {
    pending: 'bg-slate-800 border-slate-600',
    processing: 'bg-blue-950 border-blue-700',
    interpreting: 'bg-violet-950 border-violet-700',
    answered: 'bg-emerald-950 border-emerald-700',
    complete: 'bg-emerald-950 border-emerald-700',
    failed: 'bg-red-950 border-red-800',
  };
  return colors[status] ?? 'bg-slate-800 border-slate-600';
}
