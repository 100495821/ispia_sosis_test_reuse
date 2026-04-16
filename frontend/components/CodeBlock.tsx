"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { cn } from "@/lib/utils";

type Props = {
  code: string;
  language?: string;
  fileName?: string;
};

export function CodeBlock({ code, language = "java", fileName }: Props) {
  const [copied, setCopied] = useState(false);

  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      // Silently ignore — clipboard may be unavailable in some contexts
    }
  };

  return (
    <div className="overflow-hidden rounded-2xl border border-white/5 bg-ink-900/80 shadow-card">
      {/* Title bar */}
      <div className="flex items-center justify-between border-b border-white/5 bg-ink-800/60 px-4 py-2.5">
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <div className="flex items-center gap-1">
            <span className="h-2.5 w-2.5 rounded-full bg-red-400/70" />
            <span className="h-2.5 w-2.5 rounded-full bg-amber-400/70" />
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-400/70" />
          </div>
          <span className="ml-2 font-mono">{fileName ?? `snippet.${language}`}</span>
        </div>
        <button
          type="button"
          onClick={onCopy}
          className={cn(
            "inline-flex items-center gap-1.5 rounded-md border border-white/10 bg-white/5 px-2.5 py-1 text-xs font-medium transition-colors",
            copied ? "text-emerald-300" : "text-slate-200 hover:bg-white/10",
          )}
        >
          {copied ? (
            <>
              <Check className="h-3.5 w-3.5" />
              Copied
            </>
          ) : (
            <>
              <Copy className="h-3.5 w-3.5" />
              Copy
            </>
          )}
        </button>
      </div>

      {/* Highlighted code */}
      <SyntaxHighlighter
        language={language}
        style={oneDark}
        wrapLongLines
        customStyle={{
          margin: 0,
          padding: "20px 24px",
          background: "transparent",
          fontSize: 13.5,
          lineHeight: 1.7,
          fontFamily: "var(--font-jetbrains), ui-monospace, monospace",
        }}
        codeTagProps={{
          style: {
            fontFamily: "var(--font-jetbrains), ui-monospace, monospace",
          },
        }}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );
}
