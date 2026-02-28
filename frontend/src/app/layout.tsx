import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import Sidebar from '@/components/Sidebar';

const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-inter',
});

export const metadata: Metadata = {
  title: 'OpenDocs Gateway',
  description: 'Document intelligence on AMD MI300X',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <body className={`${inter.className} min-h-screen`}>
        <Sidebar />
        <main className="lg:pl-56">
          <div className="mx-auto max-w-3xl px-6 py-10 lg:py-14">
            {children}
          </div>
        </main>
      </body>
    </html>
  );
}
