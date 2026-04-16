"use client";

import { useCallback, useRef, useState } from "react";
import { FileCode, Upload, X } from "lucide-react";
import { cn } from "@/lib/utils";

const ACCEPTED_EXT = [".java", ".txt"];
const MAX_BYTES = 1_000_000; // 1 MB — prevents pasting huge files into the textarea

type Props = {
  value: string;
  onChange: (next: string) => void;
  disabled?: boolean;
};

export function CodeInput({ value, onChange, disabled }: Props) {
  const [isDragging, setIsDragging] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);
  const [readError, setReadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const readFile = useCallback(
    async (file: File) => {
      setReadError(null);

      const ext = "." + (file.name.split(".").pop()?.toLowerCase() ?? "");
      if (!ACCEPTED_EXT.includes(ext)) {
        setReadError(`Unsupported file type. Accepted: ${ACCEPTED_EXT.join(", ")}`);
        return;
      }
      if (file.size > MAX_BYTES) {
        setReadError(`File is too large (${(file.size / 1024).toFixed(0)} KB). Max 1 MB.`);
        return;
      }

      const text = await file.text();
      onChange(text);
      setFileName(file.name);
    },
    [onChange],
  );

  const onDrop = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      setIsDragging(false);
      if (disabled) return;
      const file = event.dataTransfer.files?.[0];
      if (file) void readFile(file);
    },
    [disabled, readFile],
  );

  const onBrowseClick = () => {
    if (disabled) return;
    fileInputRef.current?.click();
  };

  const onFileChosen = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) void readFile(file);
    // reset input so selecting the same file twice still fires change
    event.target.value = "";
  };

  const clear = () => {
    onChange("");
    setFileName(null);
    setReadError(null);
  };

  const charCount = value.length;
  const lineCount = value ? value.split("\n").length : 0;

  return (
    <div
      className={cn(
        "group relative rounded-2xl border transition-all duration-200",
        isDragging
          ? "border-brand-400/60 bg-brand-500/5 shadow-glow"
          : "border-white/5 bg-ink-800/60",
        "backdrop-blur-xl",
      )}
      onDragOver={(event) => {
        event.preventDefault();
        if (!disabled) setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={onDrop}
    >
      {/* Header row */}
      <div className="flex items-center justify-between border-b border-white/5 px-4 py-2.5">
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <FileCode className="h-3.5 w-3.5" />
          <span>
            {fileName ? (
              <>
                <span className="text-slate-200">{fileName}</span>
                <span className="mx-2 text-slate-600">·</span>
                <span>loaded from file</span>
              </>
            ) : (
              "Java focal method"
            )}
          </span>
        </div>
        <div className="flex items-center gap-3 text-[11px] text-slate-500">
          <span>{lineCount} lines</span>
          <span>·</span>
          <span>{charCount} chars</span>
          {value && (
            <button
              type="button"
              onClick={clear}
              className="ml-1 inline-flex items-center gap-1 rounded-md px-1.5 py-1 text-slate-400 transition-colors hover:bg-white/5 hover:text-slate-200"
              aria-label="Clear input"
            >
              <X className="h-3.5 w-3.5" />
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Textarea */}
      <div className="relative">
        <textarea
          value={value}
          onChange={(event) => onChange(event.target.value)}
          disabled={disabled}
          spellCheck={false}
          placeholder={`public double calculateTotal(double discount) {
    double sum = 0;
    for (Item item : items) {
        sum += item.price();
    }
    return sum * (1 - discount);
}`}
          className={cn(
            "block min-h-[260px] w-full resize-y bg-transparent px-5 py-4",
            "font-mono text-[13px] leading-relaxed text-slate-100",
            "placeholder:text-slate-600 focus:outline-none",
            disabled && "cursor-not-allowed opacity-60",
          )}
        />

        {/* Drag overlay */}
        {isDragging && (
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center rounded-b-2xl bg-ink-900/70 backdrop-blur-sm">
            <div className="flex flex-col items-center gap-2 text-brand-300">
              <Upload className="h-6 w-6" />
              <span className="text-sm font-medium">Drop your .java file to load it</span>
            </div>
          </div>
        )}
      </div>

      {/* Footer row */}
      <div className="flex flex-col gap-2 border-t border-white/5 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="text-xs text-slate-500">
          Drag &amp; drop a <span className="text-slate-300">.java</span> file,
          paste code directly, or browse from your device.
        </div>
        <div className="flex items-center gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept={ACCEPTED_EXT.join(",")}
            onChange={onFileChosen}
            className="hidden"
          />
          <button
            type="button"
            onClick={onBrowseClick}
            disabled={disabled}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-medium text-slate-200",
              "transition-colors hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-50",
            )}
          >
            <Upload className="h-3.5 w-3.5" />
            Upload file
          </button>
        </div>
      </div>

      {readError && (
        <div className="border-t border-red-500/20 bg-red-500/5 px-4 py-2 text-xs text-red-300">
          {readError}
        </div>
      )}
    </div>
  );
}
