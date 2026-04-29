"use client";

import { useState } from "react";
import { Header } from "@/components/Header";
import { Hero } from "@/components/Hero";
import { CodeInput } from "@/components/CodeInput";
import { GenerateButton } from "@/components/GenerateButton";
import { ResultsSection } from "@/components/ResultsSection";
import { useResultsStore } from "@/lib/store";
import { generateFromBackend } from "@/lib/api";

export default function HomePage() {
  const [code, setCode] = useState("");

  const status = useResultsStore((state) => state.status);
  const result = useResultsStore((state) => state.result);
  const error = useResultsStore((state) => state.error);
  const setLoading = useResultsStore((state) => state.setLoading);
  const setResult = useResultsStore((state) => state.setResult);
  const setError = useResultsStore((state) => state.setError);

  const isLoading = status === "loading";
  const hasInput = code.trim().length > 0;

  const handleGenerate = async () => {
    if (!hasInput || isLoading) return;
    setLoading();
    try {
      const generated = await generateFromBackend({
        focalMethod: code,
        topK: 5,
      });
      setResult(generated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed");
    }
  };

  return (
    <>
      <Header />
      <main className="mx-auto max-w-6xl px-6 pb-24">
        <Hero />

        {/* Input card */}
        <section className="mx-auto max-w-3xl">
          <CodeInput value={code} onChange={setCode} disabled={isLoading} />

          <div className="mt-6 flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
            <GenerateButton
              onClick={handleGenerate}
              disabled={!hasInput}
              loading={isLoading}
            />
            {!hasInput && (
              <span className="text-xs text-slate-500">
                Paste, upload, or drop a Java method to enable generation.
              </span>
            )}
          </div>

          {error && (
            <p className="mt-4 text-center text-sm text-rose-300">{error}</p>
          )}
        </section>

        {/* Results */}
        {result && !isLoading && <ResultsSection result={result} />}

        {/* Empty state when no results yet */}
        {!result && !isLoading && (
          <section className="mx-auto mt-20 max-w-3xl animate-fade-in text-center">
            <div className="mx-auto inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[11px] font-medium text-slate-400">
              <span className="h-1.5 w-1.5 rounded-full bg-brand-400" />
              Waiting for input
            </div>
            <p className="mx-auto mt-3 max-w-lg text-sm text-slate-500">
              Recommendations will appear here once you generate them. Each card
              is clickable and opens a copy-ready code view.
            </p>
          </section>
        )}
      </main>

      <footer className="border-t border-white/5 py-6 text-center text-xs text-slate-500">
        SOSIS · Task 3.4 — Test Reuse &amp; Amplification · MVP preview
      </footer>
    </>
  );
}
