"use client";

import { Loader2, Wand2 } from "lucide-react";
import { cn } from "@/lib/utils";

type Props = {
  onClick: () => void;
  disabled?: boolean;
  loading?: boolean;
};

export function GenerateButton({ onClick, disabled, loading }: Props) {
  const isInactive = disabled || loading;

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={isInactive}
      className={cn(
        "relative inline-flex h-12 min-w-[220px] items-center justify-center gap-2 overflow-hidden rounded-xl px-6 text-sm font-semibold text-white transition-all duration-200",
        "bg-gradient-to-r from-brand-600 via-brand-500 to-accent-500",
        "shadow-glow hover:shadow-[0_0_0_1px_rgba(99,102,241,0.4),0_14px_50px_-10px_rgba(99,102,241,0.55)]",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2 focus-visible:ring-offset-ink-950",
        "disabled:cursor-not-allowed disabled:opacity-40 disabled:shadow-none disabled:hover:shadow-none",
      )}
    >
      {/* Shimmer sweep only when enabled and idle */}
      {!isInactive && (
        <span className="pointer-events-none absolute inset-0 cta-shimmer animate-shimmer" />
      )}
      <span className="relative inline-flex items-center gap-2">
        {loading ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Analyzing your code…
          </>
        ) : (
          <>
            <Wand2 className="h-4 w-4" />
            Generate recommendations
          </>
        )}
      </span>
    </button>
  );
}
