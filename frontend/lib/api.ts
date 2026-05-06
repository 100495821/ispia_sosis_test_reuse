import type { GenerationResult, TestCase } from "./types";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL?.trim() || "http://localhost:8000";

type GenerateRequest = {
  focalMethod: string;
  topK?: number;
  skipGeneration?: boolean;
};

export type BackendStatus = {
  ready: boolean;
  stage: string;
  stageIndex: number;
  totalStages: number;
  error: string | null;
};

export async function getBackendStatus(): Promise<BackendStatus> {
  const response = await fetch(`${BACKEND_URL}/status`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Status check failed (${response.status})`);
  }
  return response.json() as Promise<BackendStatus>;
}

type StreamCallbacks = {
  onReusable: (partial: Pick<GenerationResult, "focalMethod" | "reusable">) => void;
  onAmplified: (amplified: TestCase, generatedAt: number) => void;
};

export async function streamFromBackend(
  payload: GenerateRequest,
  callbacks: StreamCallbacks,
): Promise<void> {
  const response = await fetch(`${BACKEND_URL}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let message = `Backend request failed (${response.status})`;
    try {
      const body = await response.json();
      if (typeof body?.detail === "string") message = body.detail;
    } catch { /* keep fallback */ }
    throw new Error(message);
  }

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const json = line.slice(6).trim();
      if (!json) continue;
      const event = JSON.parse(json) as Record<string, unknown>;
      if (event.type === "reusable") {
        callbacks.onReusable({
          focalMethod: event.focalMethod as string,
          reusable: event.reusable as TestCase[],
        });
      } else if (event.type === "amplified") {
        callbacks.onAmplified(event.amplified as TestCase, event.generatedAt as number);
      }
    }
  }
}
