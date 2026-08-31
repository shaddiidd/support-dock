import { Outlet } from "react-router-dom";

import { BusinessProvider, useBusinesses } from "../workspace/BusinessContext";
import { BusinessDialogProvider } from "../workspace/BusinessDialogs";
import { Sidebar } from "./Sidebar";
import { BootScreen } from "./ui";

function WorkspaceFrame() {
  const { ready } = useBusinesses();

  if (!ready) {
    return <BootScreen>Loading businesses…</BootScreen>;
  }

  return (
    <div className="flex h-dvh flex-col overflow-hidden lg:flex-row">
      <Sidebar />
      <main className="min-h-0 min-w-0 flex-1 overflow-hidden bg-surface">
        <Outlet />
      </main>
    </div>
  );
}

export function AppLayout() {
  return (
    <BusinessProvider>
      <BusinessDialogProvider>
        <WorkspaceFrame />
      </BusinessDialogProvider>
    </BusinessProvider>
  );
}
