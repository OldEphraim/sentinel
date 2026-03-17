'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import type { GeoJsonPolygon } from '@sentinel/types';
import { createWatch } from '@/lib/api';

// MapLibre must be dynamically imported (SSR would fail)
const AoiMap = dynamic(() => import('@/components/AoiMap'), { ssr: false });

const SENSOR_OPTIONS = [
  { value: 'auto', label: 'Auto — let the agent decide', icon: '🛰️' },
  { value: 'optical', label: 'Optical — visible light imagery', icon: '🌤' },
  { value: 'sar', label: 'SAR — radar, works through clouds', icon: '📡' },
  { value: 'free', label: 'Free — Sentinel-2 open data (10m)', icon: '🌍' },
];

const FREQUENCY_OPTIONS = [
  { value: 'once', label: 'Once' },
  { value: 'daily', label: 'Daily' },
  { value: 'weekly', label: 'Weekly' },
  { value: 'monthly', label: 'Monthly' },
];

const EXAMPLE_QUESTIONS = [
  'How many cargo vessels are anchored here?',
  'Is there active construction at this site?',
  'Has the vegetation coverage changed in the last 30 days?',
  'How many vehicles are in this parking area?',
  'What is the current water extent of this reservoir?',
];

export default function NewWatchPage() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [question, setQuestion] = useState('');
  const [aoi, setAoi] = useState<GeoJsonPolygon | null>(null);
  const [sensorPreference, setSensorPreference] = useState('auto');
  const [frequency, setFrequency] = useState('once');
  const [alertThreshold, setAlertThreshold] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit = name.trim() && question.trim() && aoi !== null && !submitting;

  const handleSubmit = async () => {
    if (!canSubmit || !aoi) return;
    setSubmitting(true);
    setError(null);
    try {
      const watch = await createWatch({
        name: name.trim(),
        question: question.trim(),
        aoi,
        sensor_preference: sensorPreference,
        frequency,
        alert_threshold: alertThreshold.trim() || undefined,
      }) as Record<string, unknown>;
      router.push(`/watches/${watch['id'] as string}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create watch');
      setSubmitting(false);
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-6">New Watch</h1>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Form */}
        <div className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1.5">
              Watch name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Port of Rotterdam vessel count"
              className="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-blue-500 placeholder:text-slate-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1.5">
              Question
            </label>
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              rows={3}
              placeholder="Ask anything about this location..."
              className="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-blue-500 placeholder:text-slate-500 resize-none"
            />
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {EXAMPLE_QUESTIONS.map((q) => (
                <button
                  key={q}
                  type="button"
                  onClick={() => setQuestion(q)}
                  className="text-xs bg-slate-800 hover:bg-slate-700 border border-slate-600 rounded px-2 py-1 text-slate-400 hover:text-slate-200 transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1.5">
              Sensor preference
            </label>
            <div className="space-y-2">
              {SENSOR_OPTIONS.map((opt) => (
                <label key={opt.value} className="flex items-center gap-3 cursor-pointer group">
                  <input
                    type="radio"
                    name="sensor"
                    value={opt.value}
                    checked={sensorPreference === opt.value}
                    onChange={() => setSensorPreference(opt.value)}
                    className="accent-blue-500"
                  />
                  <span className="text-lg">{opt.icon}</span>
                  <span className="text-sm text-slate-300 group-hover:text-white transition-colors">
                    {opt.label}
                  </span>
                </label>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1.5">
              Frequency
            </label>
            <select
              value={frequency}
              onChange={(e) => setFrequency(e.target.value)}
              className="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-blue-500"
            >
              {FREQUENCY_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1.5">
              Alert threshold{' '}
              <span className="text-slate-500 font-normal">(optional)</span>
            </label>
            <input
              type="text"
              value={alertThreshold}
              onChange={(e) => setAlertThreshold(e.target.value)}
              placeholder='e.g. "fewer than 5 vessels" or "more than 20% change"'
              className="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-blue-500 placeholder:text-slate-500"
            />
          </div>

          {error && (
            <div className="bg-red-950 border border-red-800 text-red-300 text-sm rounded-lg px-4 py-3">
              {error}
            </div>
          )}

          <button
            type="button"
            onClick={handleSubmit}
            disabled={!canSubmit}
            className="w-full bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:text-slate-500 disabled:cursor-not-allowed text-white py-3 rounded-lg font-medium transition-colors"
          >
            {submitting ? 'Creating watch & running agent…' : 'Create Watch'}
          </button>

          {!aoi && (
            <p className="text-amber-500 text-xs text-center">
              ↗ Draw an area of interest on the map to continue
            </p>
          )}
        </div>

        {/* Map */}
        <div className="h-[500px] lg:h-full min-h-[400px]">
          <AoiMap value={aoi} onChange={setAoi} />
        </div>
      </div>
    </div>
  );
}
