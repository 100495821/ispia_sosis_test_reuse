"use client";

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type { GenerationResult, TestCase } from "./types";

type Status = "idle" | "loading" | "retrieving" | "generating" | "ready" | "error";

type ResultsState = {
  status: Status;
  result: GenerationResult | null;
  error: string | null;

  setLoading: () => void;
  setReusable: (focalMethod: string, reusable: GenerationResult["reusable"]) => void;
  setAmplified: (amplified: TestCase, generatedAt: number) => void;
  setResult: (result: GenerationResult) => void;
  setError: (message: string) => void;
  reset: () => void;

  /** Lookup helper used by the detail page */
  findTestById: (id: string) => TestCase | undefined;
};

export const useResultsStore = create<ResultsState>()(
  persist(
    (set, get) => ({
      status: "idle",
      result: null,
      error: null,

      setLoading: () => set({ status: "loading", error: null }),

      setReusable: (focalMethod, reusable) =>
        set({
          status: "generating",
          error: null,
          result: {
            focalMethod,
            reusable,
            amplified: null,
            amplifiedLoading: true,
            generatedAt: Date.now(),
          },
        }),

      setAmplified: (amplified, generatedAt) =>
        set((state) => ({
          status: "ready",
          result: state.result
            ? { ...state.result, amplified, amplifiedLoading: false, generatedAt }
            : null,
        })),

      setResult: (result) => set({ status: "ready", result, error: null }),
      setError: (message) => set({ status: "error", error: message }),
      reset: () => set({ status: "idle", result: null, error: null }),

      findTestById: (id) => {
        const { result } = get();
        if (!result) return undefined;
        if (result.amplified?.id === id) return result.amplified;
        return result.reusable.find((t) => t.id === id);
      },
    }),
    {
      name: "sosis-results",
      storage: createJSONStorage(() => localStorage),
    },
  ),
);
