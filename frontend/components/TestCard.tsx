"use client";

import Link from "next/link";
import { ArrowUpRight, Sparkles, Reply } from "lucide-react";
import type { TestCase } from "@/lib/types";
import { cn, formatScorePercent, scoreTone } from "@/lib/utils";

type Props = {
  test: TestCase;
  rank?: number;
};

export function TestCard({ test, rank }: Props) {
  const isReusable = test.kind === "reusable";
  const tone = isReusable && typeof test.score === "number" ? scoreTone(test.score) : null;

  return (
    <Link
      href={`/test/${test.id}`}
      className={cn(
        "group relative flex flex-col gap-3 rounded-2xl border p-5 transition-all duration-200",
        "border-white/5 bg-ink-800/60 backdrop-blur-xl",
        "hover:-translate-y-0.5 hover:border-white/15 hover:bg-ink-800/80 hover:shadow-card",
      )}
    >
      {/* Top row — kind badge + score + arrow */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          {isReusable ? (
            <span className="inline-flex items-center gap-1 rounded-md border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-300">
              <Reply className="h-3 w-3" />
              Reusable
              {rank !== undefined && (
                <span className="ml-1 rounded bg-white/5 px-1 text-slate-400">
                  #{rank}
                </span>
              )}
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 rounded-md border border-accent-400/30 bg-accent-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-accent-400">
              <Sparkles className="h-3 w-3" />
              AI generated
            </span>
          )}
        </div>

        {tone && typeof test.score === "number" && (
          <div
            className={cn(
              "inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-semibold ring-1",
              tone.ring,
              tone.bg,
              tone.text,
            )}
            title={tone.label}
          >
            {formatScorePercent(test.score)}
          </div>
        )}
      </div>

      {/* Name */}
      <h3 className="truncate font-mono text-sm font-medium text-slate-100">
        {test.name}
      </h3>

      {/* Description */}
      <p className="line-clamp-3 text-sm leading-relaxed text-slate-400">
        {test.description}
      </p>

      {/* Footer */}
      <div className="mt-auto flex items-center justify-between pt-2">
        <span className="text-[11px] text-slate-500">
          Click to view full code
        </span>
        <span className="inline-flex h-7 w-7 items-center justify-center rounded-md border border-white/5 bg-white/5 text-slate-300 transition-all group-hover:border-brand-400/40 group-hover:bg-brand-500/10 group-hover:text-brand-300">
          <ArrowUpRight className="h-3.5 w-3.5" />
        </span>
      </div>

      {/* Subtle glow on hover */}
      <div
        className="pointer-events-none absolute inset-0 rounded-2xl opacity-0 transition-opacity duration-300 group-hover:opacity-100"
        style={{
          background:
            "radial-gradient(400px circle at var(--x, 50%) var(--y, 0%), rgba(99,102,241,0.08), transparent 40%)",
        }}
      />
    </Link>
  );
}
