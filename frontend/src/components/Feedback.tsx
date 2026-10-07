import { LoaderCircle } from "lucide-react";
import type { ReactNode } from "react";

export function Loading({ label = "Loading" }: { label?: string }) {
  return (
    <p className="loading" role="status">
      <LoaderCircle className="spin" size={20} aria-hidden="true" /> {label}
    </p>
  );
}

export function ErrorNote({ error, children }: { error?: unknown; children?: ReactNode }) {
  const message = children ?? (error instanceof Error ? error.message : "Something went wrong. Try again.");
  return (
    <p className="note note-warn" role="alert">
      {message}
    </p>
  );
}
