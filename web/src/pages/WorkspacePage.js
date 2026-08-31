import { useEffect, useState } from "react";
import { Navigate, NavLink, useNavigate, useParams } from "react-router-dom";
import {
  HiOutlineChatBubbleLeftRight,
  HiOutlineDocumentText,
  HiOutlineLink,
  HiOutlineSparkles,
  HiOutlineTicket,
} from "react-icons/hi2";

import { ChatPanel } from "../components/ChatPanel";
import { Button, cn } from "../components/ui";
import { useBusinesses } from "../workspace/BusinessContext";
import { ConnectDialog } from "../workspace/ConnectDialog";
import {
  DEFAULT_TAB,
  isWorkspaceTab,
  rememberTab,
  workspacePath,
} from "../workspace/paths";
import { AssistantPage } from "./AssistantPage";
import { KnowledgeBasePage } from "./KnowledgeBasePage";
import { TicketsPage } from "./TicketsPage";

const TABS = [
  { id: "documents", label: "Documents", icon: HiOutlineDocumentText },
  { id: "tickets", label: "Tickets", icon: HiOutlineTicket },
  { id: "assistant", label: "Assistant", icon: HiOutlineSparkles },
  { id: "chat", label: "Test chat", icon: HiOutlineChatBubbleLeftRight },
];

export function WorkspacePage() {
  const { businessId } = useParams();
  return <WorkspaceView key={businessId} />;
}

function WorkspaceView() {
  const { businessId, tab: tabParam, itemId } = useParams();
  const navigate = useNavigate();
  const { businesses, selectBusiness } = useBusinesses();
  const business = businesses.find((item) => item.id === businessId) ?? null;
  const tab = isWorkspaceTab(tabParam) ? tabParam : DEFAULT_TAB;
  const [connectOpen, setConnectOpen] = useState(false);

  useEffect(() => {
    if (business) {
      selectBusiness(business.id);
      rememberTab(tab);
    }
  }, [business, selectBusiness, tab]);

  if (!business) {
    return <Navigate to="/" replace />;
  }

  if (!tabParam || !isWorkspaceTab(tabParam)) {
    return <Navigate to={workspacePath(business.id, DEFAULT_TAB)} replace />;
  }

  if (itemId && tab !== "tickets") {
    return <Navigate to={workspacePath(business.id, tab)} replace />;
  }

  function onTicketCreated() {
    navigate(workspacePath(business.id, "tickets"));
  }

  return (
    <div className="flex h-full min-h-0 flex-col bg-surface">
      <header className="shrink-0 border-b border-line px-4 pt-4 sm:px-6 sm:pt-5">
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <div className="min-w-0 flex-1">
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-muted">
              Workspace
            </p>
            <h1 className="mt-1 truncate text-xl font-bold sm:text-2xl">{business.name}</h1>
            <p className="mt-1 line-clamp-2 text-sm text-muted">
              {[
                business.website_origin || business.website_url,
                business.contact_phone,
                business.contact_email,
              ]
                .filter(Boolean)
                .join(" · ") || "Add a website URL and contact details in business settings."}
            </p>
          </div>
          <Button
            type="button"
            variant="quiet"
            className="w-full py-2.5 sm:w-auto sm:shrink-0"
            onClick={() => setConnectOpen(true)}
          >
            <span className="inline-flex items-center justify-center gap-2">
              <HiOutlineLink className="h-4 w-4" />
              Connect
            </span>
          </Button>
        </div>
        <nav
          className="-mb-px flex gap-1 overflow-x-auto overscroll-x-contain pb-px [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
          aria-label="Workspace sections"
        >
          {TABS.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.id}
                to={workspacePath(
                  business.id,
                  item.id,
                  item.id === "tickets" ? itemId : undefined
                )}
                end={item.id !== "tickets"}
                className={({ isActive }) =>
                  cn(
                    "inline-flex shrink-0 items-center gap-2 whitespace-nowrap rounded-t-xl px-3 py-2.5 text-sm font-semibold no-underline sm:px-4",
                    isActive
                      ? "bg-paper text-ink"
                      : "text-muted hover:bg-paper/60 hover:text-ink"
                  )
                }
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </NavLink>
            );
          })}
        </nav>
      </header>
      <div className="min-h-0 flex-1 overflow-hidden">
        {tab === "documents" ? <KnowledgeBasePage business={business} /> : null}
        {tab === "tickets" ? <TicketsPage business={business} /> : null}
        {tab === "assistant" ? <AssistantPage business={business} /> : null}
        {tab === "chat" ? (
          <ChatPanel business={business} onTicketCreated={onTicketCreated} />
        ) : null}
      </div>
      <ConnectDialog
        open={connectOpen}
        business={business}
        onClose={() => setConnectOpen(false)}
      />
    </div>
  );
}
