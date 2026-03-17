'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Satellite } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { ApiError } from '@/lib/api';

type Tab = 'signin' | 'signup';

export default function LoginPage() {
  const { auth, login, signup } = useAuth();
  const router = useRouter();

  const [tab, setTab] = useState<Tab>('signin');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [demoKey, setDemoKey] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [emailError, setEmailError] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [demoKeyError, setDemoKeyError] = useState('');
  const [generalError, setGeneralError] = useState('');

  useEffect(() => {
    if (auth) router.replace('/');
  }, [auth, router]);

  const clearErrors = () => {
    setEmailError('');
    setPasswordError('');
    setDemoKeyError('');
    setGeneralError('');
  };

  const switchTab = (t: Tab) => {
    setTab(t);
    clearErrors();
  };

  const handleSubmit = async () => {
    clearErrors();
    setSubmitting(true);
    try {
      if (tab === 'signin') {
        await login(email, password);
      } else {
        await signup(email, password, demoKey);
      }
      router.replace('/');
    } catch (e) {
      if (e instanceof ApiError) {
        if (e.status === 401) {
          setPasswordError('Wrong email or password');
        } else if (e.status === 409) {
          setEmailError('Email already registered');
        } else if (e.status === 403) {
          setDemoKeyError('Invalid demo key');
        } else {
          setGeneralError(e.message);
        }
      } else {
        setGeneralError(e instanceof Error ? e.message : 'Something went wrong');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const canSubmit =
    email.trim() &&
    password.trim() &&
    (tab === 'signin' || demoKey.trim()) &&
    !submitting;

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="flex items-center justify-center gap-2 mb-8">
          <Satellite className="w-7 h-7 text-blue-400" />
          <span className="text-2xl font-semibold">Sentinel</span>
        </div>

        <div className="bg-slate-900 border border-slate-700 rounded-2xl p-8">
          {/* Tabs */}
          <div className="flex rounded-lg bg-slate-800 p-1 mb-6">
            {(['signin', 'signup'] as Tab[]).map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => switchTab(t)}
                className={`flex-1 py-2 text-sm font-medium rounded-md transition-colors ${
                  tab === t
                    ? 'bg-slate-600 text-white'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {t === 'signin' ? 'Sign In' : 'Create Account'}
              </button>
            ))}
          </div>

          <div className="space-y-4">
            {/* Email */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1.5">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && void handleSubmit()}
                placeholder="you@example.com"
                className={`w-full bg-slate-800 border rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-blue-500 placeholder:text-slate-500 ${
                  emailError ? 'border-red-500' : 'border-slate-600'
                }`}
              />
              {emailError && (
                <p className="text-red-400 text-xs mt-1">{emailError}</p>
              )}
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1.5">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && void handleSubmit()}
                placeholder="••••••••"
                className={`w-full bg-slate-800 border rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-blue-500 placeholder:text-slate-500 ${
                  passwordError ? 'border-red-500' : 'border-slate-600'
                }`}
              />
              {passwordError && (
                <p className="text-red-400 text-xs mt-1">{passwordError}</p>
              )}
            </div>

            {/* Demo key — signup only */}
            {tab === 'signup' && (
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">
                  Demo Key
                </label>
                <input
                  type="text"
                  value={demoKey}
                  onChange={(e) => setDemoKey(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && void handleSubmit()}
                  placeholder="Enter the demo access key"
                  className={`w-full bg-slate-800 border rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-blue-500 placeholder:text-slate-500 ${
                    demoKeyError ? 'border-red-500' : 'border-slate-600'
                  }`}
                />
                {demoKeyError && (
                  <p className="text-red-400 text-xs mt-1">{demoKeyError}</p>
                )}
              </div>
            )}

            {generalError && (
              <div className="bg-red-950 border border-red-800 text-red-300 text-sm rounded-lg px-4 py-3">
                {generalError}
              </div>
            )}

            <button
              type="button"
              onClick={() => void handleSubmit()}
              disabled={!canSubmit}
              className="w-full bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:text-slate-500 disabled:cursor-not-allowed text-white py-3 rounded-lg font-medium transition-colors mt-2"
            >
              {submitting
                ? tab === 'signin'
                  ? 'Signing in…'
                  : 'Creating account…'
                : tab === 'signin'
                  ? 'Sign In'
                  : 'Create Account'}
            </button>
          </div>
        </div>

        <p className="text-center text-slate-600 text-xs mt-6">
          Earth Intelligence powered by SkyFi
        </p>
      </div>
    </div>
  );
}
