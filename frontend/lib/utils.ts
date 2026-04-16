import clsx, { type ClassValue } from "clsx";

export function cn(...inputs: ClassValue[]): string {
  return clsx(inputs);
}

export function formatScorePercent(score: number): string {
  return `${Math.round(score * 100)}%`;
}

export function scoreTone(score: number): {
  ring: string;
  text: string;
  bg: string;
  label: string;
} {
  if (score >= 0.85)
    return {
      ring: "ring-emerald-400/40",
      text: "text-emerald-300",
      bg: "bg-emerald-400/10",
      label: "Excellent match",
    };
  if (score >= 0.7)
    return {
      ring: "ring-brand-400/40",
      text: "text-brand-300",
      bg: "bg-brand-400/10",
      label: "Strong match",
    };
  return {
    ring: "ring-amber-400/40",
    text: "text-amber-300",
    bg: "bg-amber-400/10",
    label: "Partial match",
  };
}
