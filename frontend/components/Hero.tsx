export function Hero() {
  return (
    <section className="relative overflow-hidden pb-10 pt-16">
      <div className="pointer-events-none absolute inset-0 bg-grid opacity-70" />
      <div className="relative mx-auto max-w-3xl px-6 text-center">
        <div className="mx-auto mb-5 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[11px] font-medium uppercase tracking-wider text-slate-300 backdrop-blur">
          <span className="h-1.5 w-1.5 rounded-full bg-gradient-to-br from-brand-400 to-accent-500" />
          Task 3.4 · Test Reuse Recommendations
        </div>
        <h1 className="bg-gradient-to-b from-white to-slate-400 bg-clip-text text-4xl font-semibold tracking-tight text-transparent sm:text-5xl">
          Find reusable tests.
          <br />
          Amplify what&apos;s missing.
        </h1>
        <p className="mx-auto mt-5 max-w-xl text-base leading-relaxed text-slate-400 sm:text-lg">
          Paste a Java focal method and let SOSIS retrieve the most relevant
          existing tests from the corpus — then generate a new test for the
          behavior your suite doesn&apos;t cover yet.
        </p>
      </div>
    </section>
  );
}
