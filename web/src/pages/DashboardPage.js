import { Navigate } from "react-router-dom";

import { Button, Eyebrow, Panel } from "../components/ui";
import { useBusinesses } from "../workspace/BusinessContext";
import { useBusinessDialogs } from "../workspace/BusinessDialogs";
import { rememberedTab, workspacePath } from "../workspace/paths";

export function DashboardPage() {
  const { activeBusiness } = useBusinesses();
  const { openCreate } = useBusinessDialogs();

  if (activeBusiness) {
    return <Navigate to={workspacePath(activeBusiness.id, rememberedTab())} replace />;
  }

  return (
    <div className="h-full overflow-y-auto px-4 py-6 sm:px-6 sm:py-8">
      <Panel>
        <Eyebrow>Get started</Eyebrow>
        <h1 className="text-2xl font-bold sm:text-3xl">Create your first business.</h1>
        <p className="mb-6 mt-2 leading-relaxed text-muted">
          Each business is its own workspace. Switch between them from the
          sidebar whenever you like.
        </p>
        <Button type="button" className="w-full sm:w-auto" onClick={openCreate}>
          New business
        </Button>
      </Panel>
    </div>
  );
}
