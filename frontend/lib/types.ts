export type TestKind = "reusable" | "amplified";

export type TestCase = {
  id: string;
  kind: TestKind;
  name: string;
  description: string;
  code: string;
  /** Cosine similarity 0..1 — only for reusable tests */
  score?: number;
};

export type GenerationResult = {
  /** The original Java focal method the user submitted */
  focalMethod: string;
  /** Top 5 retrieved reusable tests, sorted by score desc */
  reusable: TestCase[];
  /** Single AI-generated JUnit test */
  amplified: TestCase;
  /** Epoch ms — for cache-busting / result labelling */
  generatedAt: number;
};
