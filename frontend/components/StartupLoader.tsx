"use client";

import { useEffect, useRef, useState } from "react";
import { Sparkles } from "lucide-react";
import { getBackendStatus } from "@/lib/api";
import type { BackendStatus } from "@/lib/api";

const POLL_INTERVAL_MS = 600;

type Phase = "loading" | "fading" | "done";

export function StartupLoader({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<BackendStatus | null>(null);
  const [phase, setPhase] = useState<Phase>("loading");
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    const poll = async () => {
      try {
        const s = await getBackendStatus();
        setStatus(s);
        if (s.ready) {
          if (intervalRef.current) clearInterval(intervalRef.current);
          setPhase("fading");
          setTimeout(() => setPhase("done"), 700);
        }
      } catch {
        // Backend not yet reachable — keep polling
      }
    };

    poll();
    intervalRef.current = setInterval(poll, POLL_INTERVAL_MS);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  if (phase === "done") return <>{children}</>;

  const pct = status
    ? Math.round((status.stageIndex / status.totalStages) * 100)
    : 0;

  const stageLabel = status?.error
    ? `Error: ${status.error}`
    : status?.stage ?? "Connecting…";

  return (
    <>
      {/* Render children underneath so they're ready when the overlay fades */}
      {phase === "fading" && children}

      <div
        className={`fixed inset-0 z-50 flex flex-col items-center justify-center bg-ink-950 transition-opacity duration-700 ${
          phase === "fading" ? "pointer-events-none opacity-0" : "opacity-100"
        }`}
      >
        {/* Background glow matching the app */}
        <div
          className="pointer-events-none absolute inset-0"
          style={{
            backgroundImage:
              "radial-gradient(60% 50% at 50% 0%, rgba(99,102,241,0.12) 0%, rgba(99,102,241,0) 60%), radial-gradient(40% 40% at 90% 10%, rgba(168,85,247,0.10) 0%, rgba(168,85,247,0) 70%)",
          }}
        />

        <div className="relative flex flex-col items-center gap-5">
          {/* Logo */}
          <span className="relative inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-500 to-accent-500 shadow-glow">
            <Sparkles className="h-8 w-8 text-white" strokeWidth={2} />
          </span>

          <div className="text-center">
            <p className="text-xl font-semibold tracking-tight text-white">
              SOSIS
            </p>
            <p className="mt-0.5 text-sm text-slate-400">
              Test Reuse &amp; Amplification
            </p>
          </div>

          {/* Progress bar */}
          <div className="mt-4 w-72">
            <div className="relative h-1.5 w-full overflow-hidden rounded-full bg-white/10">
              <div
                className="h-full rounded-full bg-gradient-to-r from-brand-500 to-accent-500 transition-all duration-500 ease-out"
                style={{ width: `${pct}%` }}
              />
            </div>

            {/* Stage label */}
            <p className="mt-3 text-center text-xs text-slate-500">
              {stageLabel}
            </p>

            {/* Step indicators */}
            <div className="mt-4 flex items-center justify-between gap-1">
              {Array.from({ length: status?.totalStages ?? 3 }, (_, i) => (
                <div
                  key={i}
                  className={`h-0.5 flex-1 rounded-full transition-all duration-500 ${
                    i < (status?.stageIndex ?? 0)
                      ? "bg-brand-500"
                      : "bg-white/10"
                  }`}
                />
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
