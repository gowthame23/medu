import type { Metadata, Viewport } from 'next';
import './globals.css';
import { AuthProvider } from '@/context/AuthContext';

export const dynamic = 'force-dynamic';

export const metadata: Metadata = {
  title: 'Mend — The Anxiety-Free Household & Family Financial Platform',
  description: 'Anxiety-free household platform with strict dual-account privacy, 30s ritual, tomorrow radar, and 1-tap UPI intent.',
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  viewportFit: 'cover',
  themeColor: '#fafaf7',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full antialiased bg-[#f4f4f0] text-stone-900 select-none">
      <body className="min-h-full flex flex-col items-center justify-start bg-[#f4f4f0] font-sans antialiased">
        {/* Constrained Mobile Shell for Phone Form Factor */}
        <div className="w-full max-w-md min-h-screen bg-[#fafaf7] shadow-xl sm:border-x sm:border-stone-200/80 flex flex-col relative overflow-x-hidden">
          <AuthProvider>{children}</AuthProvider>
        </div>
      </body>
    </html>
  );
}
