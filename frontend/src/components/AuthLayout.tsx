import type { ReactNode } from "react";
import { LetterTiles } from "./Tiles";

export function AuthLayout({ title, intro, children }: { title: string; intro: string; children: ReactNode }) {
  return (
    <main className="auth">
      <div className="auth-brand">
        <LetterTiles word="Lexi" size="lg" />
        <p className="auth-tagline">Reading practice that goes one sound at a time.</p>
      </div>
      <section className="auth-panel" aria-labelledby="auth-title">
        <h1 id="auth-title">{title}</h1>
        <p className="muted">{intro}</p>
        {children}
      </section>
    </main>
  );
}
