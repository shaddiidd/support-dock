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
    <div className="px-6 py-8">
      <Panel>
        <Eyebrow>Get started</Eyebrow>
        <h1 className="text-3xl font-bold">Create your first business.</h1>
        <p className="mb-6 mt-2 leading-relaxed text-muted">
          Each business is its own workspace. Switch between them from the
          sidebar whenever you like.
        </p>
        <Button type="button" onClick={openCreate}>
          New business
        </Button>
      </Panel>
    </div>
  );
}
