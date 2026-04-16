# SOSIS Frontend

UI for the SOSIS Test Reuse & Amplification pipeline. Currently **fully decoupled from the backend** — it runs on mock data so you can iterate on UX without waiting on API wiring.

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

Open http://localhost:3000.

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
│   ├── mockData.ts              Fake backend response — swap later
│   ├── store.ts                 Zustand store shared by both pages
│   └── utils.ts                 cn(), score formatters, tone helpers
├── tailwind.config.ts
├── next.config.js
└── package.json
```

## Wiring the real backend later

Replace the `mockGenerate()` call in [`app/page.tsx`](app/page.tsx) with a real `fetch()` to the Python backend. Keep the return shape aligned with [`lib/types.ts`](lib/types.ts) (`GenerationResult`) and nothing else in the UI has to change.

Expected backend response:

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
    code: string;            // the Qwen-generated JUnit test
  };
  generatedAt: number;       // epoch ms
}
```
