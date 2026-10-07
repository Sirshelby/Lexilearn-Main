import { Route, Routes } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { GuestOnly, ProtectedRoute } from "./components/ProtectedRoute";
import { GamesPage } from "./pages/GamesPage";
import { HomePage } from "./pages/HomePage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { PracticePage } from "./pages/PracticePage";
import { ProgressPage } from "./pages/ProgressPage";
import { ReadingPage } from "./pages/ReadingPage";
import { RegisterPage } from "./pages/RegisterPage";
import { SettingsPage } from "./pages/SettingsPage";
import { SignInPage } from "./pages/SignInPage";
import { TutorPage } from "./pages/TutorPage";
import { WordLabPage } from "./pages/WordLabPage";

export function App() {
  return (
    <Routes>
      <Route element={<GuestOnly />}>
        <Route path="/sign-in" element={<SignInPage />} />
        <Route path="/register" element={<RegisterPage />} />
      </Route>
      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route index element={<HomePage />} />
          <Route path="practice" element={<PracticePage />} />
          <Route path="lexi" element={<TutorPage />} />
          <Route path="read" element={<ReadingPage />} />
          <Route path="word-lab" element={<WordLabPage />} />
          <Route path="games" element={<GamesPage />} />
          <Route path="progress" element={<ProgressPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
