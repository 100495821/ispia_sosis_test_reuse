import type { GenerationResult } from "./types";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL?.trim() || "http://localhost:8000";

type GenerateRequest = {
  focalMethod: string;
  topK?: number;
  skipGeneration?: boolean;
};

export async function generateFromBackend(
  payload: GenerateRequest,
): Promise<GenerationResult> {
  const response = await fetch(`${BACKEND_URL}/generate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let message = `Backend request failed (${response.status})`;
    try {
      const body = await response.json();
      if (typeof body?.detail === "string") {
        message = body.detail;
      }
    } catch {
      // Keep fallback message when no JSON body is returned.
    }
    throw new Error(message);
  }

  return (await response.json()) as GenerationResult;
}