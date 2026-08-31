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
    <div className="grid min-h-screen lg:h-screen lg:grid-cols-[280px_minmax(0,1fr)] lg:overflow-hidden">
      <Sidebar />
      <main className="min-h-0 min-w-0 bg-surface lg:h-full lg:overflow-hidden">
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
