import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Loading } from "./Feedback";

export function ProtectedRoute() {
  const { status, learner } = useAuth();
  const location = useLocation();

  if (status === "loading") {
    return (
      <main className="centre-screen">
        <Loading label="Opening LexiLearn" />
      </main>
    );
  }
  if (status === "signed_out" || !learner) {
    return <Navigate to="/sign-in" replace state={{ from: location.pathname }} />;
  }
  return <Outlet />;
}

export function GuestOnly() {
  const { status } = useAuth();
  if (status === "signed_in") return <Navigate to="/" replace />;
  return <Outlet />;
}
