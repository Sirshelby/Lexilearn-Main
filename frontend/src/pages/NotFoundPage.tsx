import { Link } from "react-router-dom";
import { LetterTiles } from "../components/Tiles";

export function NotFoundPage() {
  return (
    <main className="centre-screen stack">
      <LetterTiles word="oops" size="lg" />
      <h1>This page doesn't exist</h1>
      <p>The link may be old or mistyped.</p>
      <Link to="/" className="btn">
        Go to the home page
      </Link>
    </main>
  );
}
