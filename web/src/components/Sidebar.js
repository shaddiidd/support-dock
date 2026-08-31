import { Link, useParams } from "react-router-dom";
import {
  HiOutlineArrowRightOnRectangle,
  HiOutlinePencilSquare,
  HiOutlinePlus,
  HiOutlineTrash,
} from "react-icons/hi2";

import { useAuth } from "../auth/AuthContext";
import { useBusinesses } from "../workspace/BusinessContext";
import { useBusinessDialogs } from "../workspace/BusinessDialogs";
import { DEFAULT_TAB, isWorkspaceTab, workspacePath } from "../workspace/paths";
import { IconButton } from "./Dialog";
import { BrandMark } from "./Logo";
import { Button, cn } from "./ui";

export function Sidebar() {
  const { user, logout } = useAuth();
  const { businesses } = useBusinesses();
  const { openCreate, openEdit, openDelete } = useBusinessDialogs();
  const { businessId, tab } = useParams();
  const currentTab = isWorkspaceTab(tab) ? tab : DEFAULT_TAB;

  return (
    <aside className="flex h-screen flex-col overflow-y-auto bg-harbor-deep px-4 py-5 text-paper lg:h-full lg:min-h-0">
      <BrandMark size="sm" inverted kicker="Workspaces" />

      <nav
        className="my-5 grid flex-1 auto-cols-[minmax(220px,1fr)] grid-flow-col content-start gap-1 overflow-auto lg:grid-flow-row lg:auto-cols-auto"
        aria-label="Businesses"
      >
        {businesses.length === 0 ? (
          <p className="text-sm text-paper/60">No businesses yet.</p>
        ) : (
          businesses.map((business) => {
            const isActive = business.id === businessId;
            return (
              <div
                key={business.id}
                className={cn(
                  "flex items-center gap-1 rounded-xl pr-1",
                  isActive ? "bg-paper/15" : "hover:bg-paper/10"
                )}
              >
                <Link
                  to={workspacePath(business.id, currentTab)}
                  className="flex min-w-0 flex-1 items-center gap-3 px-2.5 py-2.5 text-left text-paper no-underline"
                  aria-current={isActive ? "page" : undefined}
                >
                  <span
                    className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-copper text-xs font-bold text-surface"
                    aria-hidden="true"
                  >
                    {business.name.slice(0, 1).toUpperCase()}
                  </span>
                  <span className="grid min-w-0 gap-0.5">
                    <span className="truncate">{business.name}</span>
                    {business.description ? (
                      <span className="truncate text-xs text-paper/60">
                        {business.description}
                      </span>
                    ) : null}
                  </span>
                </Link>
                <IconButton label="Edit business" onClick={() => openEdit(business)}>
                  <HiOutlinePencilSquare className="h-4 w-4" />
                </IconButton>
                <IconButton label="Delete business" onClick={() => openDelete(business)}>
                  <HiOutlineTrash className="h-4 w-4" />
                </IconButton>
              </div>
            );
          })
        )}
      </nav>

      <div className="mb-4">
        <Button type="button" variant="dashed" onClick={openCreate}>
          <span className="inline-flex items-center justify-center gap-2">
            <HiOutlinePlus className="h-4 w-4" />
            New business
          </span>
        </Button>
      </div>

      <div className="flex items-center justify-between gap-3 border-t border-paper/10 pt-4">
        <span className="truncate text-sm">{user.name}</span>
        <IconButton label="Sign out" onClick={logout}>
          <HiOutlineArrowRightOnRectangle className="h-5 w-5" />
        </IconButton>
      </div>
    </aside>
  );
}
