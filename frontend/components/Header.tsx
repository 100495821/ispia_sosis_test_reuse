import Link from "next/link";
import { Sparkles } from "lucide-react";

export function Header() {
  return (
    <header className="sticky top-0 z-40 border-b border-white/5 bg-ink-950/60 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
        <Link href="/" className="group flex items-center gap-2.5">
          <span className="relative inline-flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-brand-500 to-accent-500 shadow-glow">
            <Sparkles className="h-4 w-4 text-white" strokeWidth={2.5} />
          </span>
          <span className="flex flex-col leading-tight">
            <span className="text-sm font-semibold tracking-tight text-white">
              SOSIS
            </span>
            <span className="text-[11px] font-medium text-slate-400">
              Test Reuse &amp; Amplification
            </span>
          </span>
        </Link>

        <nav className="hidden items-center gap-6 text-sm text-slate-400 md:flex">
          <a
            className="transition-colors hover:text-slate-100"
            href="https://github.com/microsoft/methods2test"
            target="_blank"
            rel="noreferrer"
          >
            Dataset
          </a>
          <a
            className="transition-colors hover:text-slate-100"
            href="#"
          >
            Docs
          </a>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[11px] font-medium text-slate-300">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            MVP preview
          </span>
        </nav>
      </div>
    </header>
  );
}
