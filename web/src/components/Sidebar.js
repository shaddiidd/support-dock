import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  HiOutlineArrowRightOnRectangle,
  HiOutlineBars3,
  HiOutlinePencilSquare,
  HiOutlinePlus,
  HiOutlineTrash,
  HiOutlineXMark,
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
  const { businesses, activeBusiness } = useBusinesses();
  const { openCreate, openEdit, openDelete } = useBusinessDialogs();
  const { businessId, tab } = useParams();
  const currentTab = isWorkspaceTab(tab) ? tab : DEFAULT_TAB;
  const [open, setOpen] = useState(false);

  useEffect(() => {
    setOpen(false);
  }, [businessId]);

  useEffect(() => {
    function onKeyDown(event) {
      if (event.key === "Escape") {
        setOpen(false);
      }
    }

    const media = window.matchMedia("(min-width: 1024px)");
    function onViewportChange() {
      if (media.matches) {
        setOpen(false);
      }
    }

    if (open) {
      document.addEventListener("keydown", onKeyDown);
    }
    media.addEventListener("change", onViewportChange);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      media.removeEventListener("change", onViewportChange);
    };
  }, [open]);

  function closeAnd(action) {
    return (...args) => {
      setOpen(false);
      action(...args);
    };
  }

  const bodyProps = {
    businesses,
    businessId,
    currentTab,
    user,
    onCreate: closeAnd(openCreate),
    onEdit: closeAnd(openEdit),
    onDelete: closeAnd(openDelete),
    onLogout: closeAnd(logout),
    onNavigate: () => setOpen(false),
  };

  return (
    <>
      <header className="flex shrink-0 items-center gap-3 bg-harbor-deep px-3 py-3 pt-[max(0.75rem,env(safe-area-inset-top))] text-paper lg:hidden">
        <button
          type="button"
          className="grid h-10 w-10 shrink-0 place-items-center rounded-lg text-paper hover:bg-paper/10"
          aria-label="Open workspaces"
          aria-expanded={open}
          onClick={() => setOpen(true)}
        >
          <HiOutlineBars3 className="h-6 w-6" />
        </button>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-bold">
            {activeBusiness?.name || "Support Dock"}
          </p>
          <p className="truncate text-xs text-paper/60">
            {activeBusiness ? "Workspace" : "Workspaces"}
          </p>
        </div>
        <IconButton label="Sign out" onClick={logout}>
          <HiOutlineArrowRightOnRectangle className="h-5 w-5" />
        </IconButton>
      </header>

      {open ? (
        <div className="fixed inset-0 z-40 flex lg:hidden">
          <button
            type="button"
            className="absolute inset-0 bg-harbor-deep/50"
            aria-label="Close workspaces"
            onClick={() => setOpen(false)}
          />
          <aside className="relative z-10 flex h-full w-[min(18rem,88vw)] flex-col overflow-y-auto bg-harbor-deep px-4 py-5 pb-[max(1.25rem,env(safe-area-inset-bottom))] text-paper shadow-card">
            <div className="mb-1 flex justify-end">
              <IconButton label="Close workspaces" onClick={() => setOpen(false)}>
                <HiOutlineXMark className="h-5 w-5" />
              </IconButton>
            </div>
            <SidebarBody {...bodyProps} />
          </aside>
        </div>
      ) : null}

      <aside className="hidden h-full min-h-0 w-[280px] shrink-0 flex-col overflow-y-auto bg-harbor-deep px-4 py-5 text-paper lg:flex">
        <SidebarBody {...bodyProps} />
      </aside>
    </>
  );
}

function SidebarBody({
  businesses,
  businessId,
  currentTab,
  user,
  onCreate,
  onEdit,
  onDelete,
  onLogout,
  onNavigate,
}) {
  return (
    <>
      <BrandMark size="sm" inverted kicker="Workspaces" />

      <nav
        className="my-5 grid flex-1 content-start gap-1 overflow-auto"
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
                  onClick={onNavigate}
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
                <IconButton label="Edit business" onClick={() => onEdit(business)}>
                  <HiOutlinePencilSquare className="h-4 w-4" />
                </IconButton>
                <IconButton label="Delete business" onClick={() => onDelete(business)}>
                  <HiOutlineTrash className="h-4 w-4" />
                </IconButton>
              </div>
            );
          })
        )}
      </nav>

      <div className="mb-4">
        <Button type="button" variant="dashed" onClick={onCreate}>
          <span className="inline-flex items-center justify-center gap-2">
            <HiOutlinePlus className="h-4 w-4" />
            New business
          </span>
        </Button>
      </div>

      <div className="flex items-center justify-between gap-3 border-t border-paper/10 pt-4">
        <span className="truncate text-sm">{user.name}</span>
        <IconButton label="Sign out" onClick={onLogout}>
          <HiOutlineArrowRightOnRectangle className="h-5 w-5" />
        </IconButton>
      </div>
    </>
  );
}
