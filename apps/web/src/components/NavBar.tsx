'use client';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Satellite } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

export default function NavBar() {
  const { auth, logout } = useAuth();
  const router = useRouter();

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  return (
    <nav className="border-b border-slate-800 px-6 py-4 flex items-center gap-4">
      <Link
        href="/"
        className="flex items-center gap-2 font-semibold text-lg hover:text-slate-300 transition-colors"
      >
        <Satellite className="w-5 h-5 text-blue-400" />
        Sentinel
      </Link>
      <Link href="/" className="text-sm text-slate-400 hover:text-slate-200 transition-colors">
        Dashboard
      </Link>
      <span className="text-slate-600 text-sm">Earth Intelligence powered by SkyFi</span>
      <div className="ml-auto flex items-center gap-4">
        {auth ? (
          <>
            <span className="text-slate-500 text-sm truncate max-w-[200px]">
              {auth.user.email}
            </span>
            <button
              type="button"
              onClick={handleLogout}
              className="text-slate-400 hover:text-slate-200 text-sm transition-colors"
            >
              Sign out
            </button>
            <Link
              href="/watches/new"
              className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors"
            >
              + New Watch
            </Link>
          </>
        ) : (
          <Link
            href="/login"
            className="text-slate-400 hover:text-slate-200 text-sm transition-colors"
          >
            Sign in
          </Link>
        )}
      </div>
    </nav>
  );
}
