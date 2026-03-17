import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import Link from 'next/link';
import { Satellite } from 'lucide-react';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Sentinel — Earth Intelligence',
  description: 'Autonomous satellite monitoring powered by SkyFi',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-slate-950 text-slate-100 min-h-screen`}>
        <nav className="border-b border-slate-800 px-6 py-4 flex items-center gap-4">
          <Link href="/" className="flex items-center gap-2 font-semibold text-lg hover:text-slate-300 transition-colors">
            <Satellite className="w-5 h-5 text-blue-400" />
            Sentinel
          </Link>
          <span className="text-slate-600 text-sm">Earth Intelligence powered by SkyFi</span>
          <div className="ml-auto">
            <Link
              href="/watches/new"
              className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors"
            >
              + New Watch
            </Link>
          </div>
        </nav>
        <main className="max-w-6xl mx-auto px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
