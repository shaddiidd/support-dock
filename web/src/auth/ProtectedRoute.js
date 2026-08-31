import { Navigate, Outlet, useLocation } from "react-router-dom";

import { BootScreen } from "../components/ui";
import { useAuth } from "./AuthContext";

export function ProtectedRoute() {
  const { ready, isAuthenticated } = useAuth();
  const location = useLocation();

  if (!ready) {
    return <BootScreen>Loading workspace…</BootScreen>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <Outlet />;
}
