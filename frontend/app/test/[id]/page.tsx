"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Reply, Sparkles } from "lucide-react";
import { CodeBlock } from "@/components/CodeBlock";
import { Header } from "@/components/Header";
import { useResultsStore } from "@/lib/store";
import { cn, formatScorePercent, scoreTone } from "@/lib/utils";
import type { TestCase } from "@/lib/types";

export default function TestDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const findTestById = useResultsStore((state) => state.findTestById);

  // Guard against SSR hydration mismatches: only read store after mount
  const [hydrated, setHydrated] = useState(false);
  const [test, setTest] = useState<TestCase | undefined>(undefined);

  useEffect(() => {
    setHydrated(true);
    setTest(findTestById(params.id));
  }, [params.id, findTestById]);

  if (!hydrated) {
    return <Skeleton />;
  }

  if (!test) {
    return <NotFound onBack={() => router.push("/")} />;
  }

  const isReusable = test.kind === "reusable";
  const tone = isReusable && typeof test.score === "number" ? scoreTone(test.score) : null;

  return (
    <>
      <Header />
      <main className="mx-auto max-w-4xl px-6 py-10">
        <Link
          href="/"
          className="group inline-flex items-center gap-2 text-sm text-slate-400 transition-colors hover:text-slate-200"
        >
          <ArrowLeft className="h-4 w-4 transition-transform group-hover:-translate-x-0.5" />
          Back to results
        </Link>

        <div className="mt-6 animate-fade-in">
          <div className="flex flex-wrap items-center gap-2">
            {isReusable ? (
              <span className="inline-flex items-center gap-1.5 rounded-md border border-white/10 bg-white/5 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wider text-slate-300">
                <Reply className="h-3 w-3" />
                Reusable test
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 rounded-md border border-accent-400/30 bg-accent-500/10 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wider text-accent-400">
                <Sparkles className="h-3 w-3" />
                AI-amplified test
              </span>
            )}

            {tone && typeof test.score === "number" && (
              <span
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-semibold ring-1",
                  tone.ring,
                  tone.bg,
                  tone.text,
                )}
              >
                {formatScorePercent(test.score)} — {tone.label}
              </span>
            )}
          </div>

          <h1 className="mt-4 break-words font-mono text-2xl font-semibold tracking-tight text-white sm:text-3xl">
            {test.name}
          </h1>
          <p className="mt-3 max-w-2xl text-base leading-relaxed text-slate-400">
            {test.description}
          </p>

          <div className="mt-8">
            <CodeBlock
              code={test.code}
              language="java"
              fileName={`${test.name}.java`}
            />
          </div>

          <div className="mt-6 rounded-xl border border-white/5 bg-ink-800/40 px-4 py-3 text-xs text-slate-400">
            <span className="text-slate-300">Tip:</span> Drop this test into your
            project&apos;s <span className="font-mono text-slate-200">src/test/java</span>{" "}
            directory, adjust imports for your package layout, and run it with{" "}
            <span className="font-mono text-slate-200">mvn test</span> or{" "}
            <span className="font-mono text-slate-200">./gradlew test</span>.
          </div>
        </div>
      </main>
    </>
  );
}

function Skeleton() {
  return (
    <>
      <Header />
      <main className="mx-auto max-w-4xl px-6 py-10">
        <div className="h-4 w-32 animate-pulse rounded bg-white/5" />
        <div className="mt-8 h-8 w-2/3 animate-pulse rounded bg-white/5" />
        <div className="mt-4 h-4 w-full animate-pulse rounded bg-white/5" />
        <div className="mt-10 h-72 animate-pulse rounded-2xl bg-white/5" />
      </main>
    </>
  );
}

function NotFound({ onBack }: { onBack: () => void }) {
  return (
    <>
      <Header />
      <main className="mx-auto max-w-2xl px-6 py-20 text-center">
        <h1 className="text-2xl font-semibold text-white">Test not found</h1>
        <p className="mt-2 text-sm text-slate-400">
          This test is no longer in the current result set. Generate a new
          recommendation and try again.
        </p>
        <button
          onClick={onBack}
          className="mt-6 inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-sm text-slate-200 transition-colors hover:bg-white/10"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to home
        </button>
      </main>
    </>
  );
}
