'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const NAV = [
  { href: '/', label: 'Home' },
  { href: '/ask', label: 'Ask' },
  { href: '/extract', label: 'Extract' },
  { href: '/compare', label: 'Compare' },
  { href: '/multi', label: 'Multi-doc' },
  { href: '/documents', label: 'Documents' },
  { href: '/benchmark', label: 'Metrics' },
];

export default function Sidebar() {
  const path = usePathname();

  return (
    <aside className="fixed inset-y-0 left-0 z-30 hidden lg:flex w-56 flex-col bg-neutral-50/70 border-r border-neutral-200/60">
      {/* Brand */}
      <Link href="/" className="flex items-center gap-2.5 px-5 h-14">
        <span className="flex h-7 w-7 items-center justify-center rounded-md bg-neutral-900 text-[11px] font-semibold text-white tracking-tight">
          OD
        </span>
        <span className="text-[13px] font-semibold text-neutral-800 tracking-tight">
          OpenDocs
        </span>
      </Link>

      {/* Upload */}
      <div className="px-3 mb-1">
        <Link
          href="/upload"
          className={`flex items-center gap-2 rounded-md px-3 py-2 text-[13px] font-medium transition-colors ${
            path === '/upload'
              ? 'bg-neutral-900 text-white'
              : 'text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900'
          }`}
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          New document
        </Link>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-3 py-2 space-y-px">
        {NAV.map((item) => {
          const active = item.href === '/' ? path === '/' : path.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`block rounded-md px-3 py-[7px] text-[13px] transition-colors ${
                active
                  ? 'bg-neutral-200/60 text-neutral-900 font-medium'
                  : 'text-neutral-500 hover:bg-neutral-100 hover:text-neutral-800'
              }`}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t border-neutral-200/60">
        <p className="text-[11px] text-neutral-400 leading-tight">
          vLLM · MI300X
        </p>
      </div>
    </aside>
  );
}
