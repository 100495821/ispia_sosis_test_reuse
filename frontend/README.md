# SOSIS Frontend

UI for the SOSIS Test Reuse & Amplification pipeline. Connected to the FastAPI backend at `http://localhost:8000` via `lib/api.ts`.

## Stack

- **Next.js 14** (App Router) + **TypeScript**
- **Tailwind CSS** for styling (custom dark theme with indigo/violet accents)
- **Zustand** (with `persist` to `localStorage`) for sharing results between pages
- **react-syntax-highlighter** (Prism) for Java code display
- **lucide-react** for icons

## Setup

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000. The backend must be running at http://localhost:8000 (or set `NEXT_PUBLIC_BACKEND_URL` to override).

To start both together from the project root:

```bash
bash run_website.sh
```

## Features

- **Java code input** via textarea, drag-and-drop, or file upload (`.java` / `.txt`, max 1 MB)
- **Generate button** — disabled until the input has content, animated while loading
- **Top 5 reusable tests** — each card shows cosine similarity %, name, description; click to open a detail view
- **AI-amplified test** — a single generated card with the same click-through behavior
- **Detail page** at `/test/[id]` with a syntax-highlighted code snippet and a one-click Copy button
- **Responsive** — single column on mobile, 2 columns on tablets, 3 columns on desktop

## File layout

```
frontend/
├── app/
│   ├── layout.tsx               Root layout, fonts
│   ├── globals.css              Theme tokens, scrollbar, selection
│   ├── page.tsx                 Home — input + results
│   └── test/[id]/page.tsx       Detail view for one test
├── components/
│   ├── Header.tsx
│   ├── Hero.tsx
│   ├── CodeInput.tsx            Textarea + drag/drop + file upload
│   ├── GenerateButton.tsx       Disabled-until-input CTA with shimmer
│   ├── ResultsSection.tsx       Reusable grid + Amplified card
│   ├── TestCard.tsx             Shared card used in both sections
│   └── CodeBlock.tsx            Prism highlighter + copy button
├── lib/
│   ├── types.ts                 TestCase, GenerationResult
│   ├── api.ts                   generateFromBackend() — calls POST /generate
│   ├── mockData.ts              Fake backend response for local dev without backend
│   ├── store.ts                 Zustand store shared by both pages
│   └── utils.ts                 cn(), score formatters, tone helpers
├── tailwind.config.ts
├── next.config.js
└── package.json
```

## Backend API

The frontend calls `POST /generate` on the backend. The response shape must match [`lib/types.ts`](lib/types.ts) (`GenerationResult`):

```ts
{
  focalMethod: string;       // echo of what the user submitted
  reusable: Array<{
    id: string;
    kind: "reusable";
    name: string;            // extracted test method name
    description: string;     // short summary (truncated focal method, etc.)
    code: string;            // full Java source of the test
    score: number;           // 0..1 cosine similarity
  }>;
  amplified: {
    id: string;
    kind: "amplified";
    name: string;
    description: string;
    code: string;            // the Qwen2.5-Coder-generated JUnit test
  };
  generatedAt: number;       // epoch ms
}
```

The backend URL defaults to `http://localhost:8000` and can be overridden with the `NEXT_PUBLIC_BACKEND_URL` environment variable.
