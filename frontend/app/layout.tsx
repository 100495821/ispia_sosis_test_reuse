import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { StartupLoader } from "@/components/StartupLoader";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains",
  display: "swap",
});

export const metadata: Metadata = {
  title: "SOSIS — Test Reuse & Amplification",
  description:
    "AI-powered recommendations for reusable JUnit tests and amplified test cases, built for software product lines.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.variable} ${jetbrains.variable}`}>
      <body className="min-h-screen font-sans" suppressHydrationWarning>
        <StartupLoader>{children}</StartupLoader>
      </body>
    </html>
  );
}
