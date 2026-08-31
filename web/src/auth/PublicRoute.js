import { Navigate, Outlet } from "react-router-dom";

import { BootScreen } from "../components/ui";
import { useAuth } from "./AuthContext";

export function PublicRoute() {
  const { ready, isAuthenticated } = useAuth();

  if (!ready) {
    return <BootScreen>Loading workspace…</BootScreen>;
  }

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}
