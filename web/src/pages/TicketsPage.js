import { useEffect, useState } from "react";
import { HiOutlineArrowLeft, HiOutlineTicket } from "react-icons/hi2";
import { Link, useNavigate, useParams } from "react-router-dom";

import * as ticketsApi from "../api/tickets";
import { useAuth } from "../auth/AuthContext";
import { Alert, cn } from "../components/ui";
import { workspacePath } from "../workspace/paths";

const PRIORITY_STYLES = {
  low: "bg-paper text-muted",
  medium: "bg-amber-50 text-amber-900",
  high: "bg-orange-50 text-orange-900",
  urgent: "bg-red-50 text-red-800",
};

const CATEGORY_LABELS = {
  payment: "Payment",
  bug: "Bug",
  account: "Account",
  refund: "Refund",
  complaint: "Complaint",
  security: "Security",
  human_request: "Human requested",
  unresolved: "Unresolved",
};

export function TicketsPage({ business }) {
  const { token } = useAuth();
  const navigate = useNavigate();
  const { itemId } = useParams();
  const isDesktop = useIsDesktop();
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    ticketsApi
      .listTickets(token, business.id)
      .then((items) => {
        if (cancelled) {
          return;
        }
        setTickets(items);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message || "Unable to load tickets");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [token, business.id]);

  useEffect(() => {
    if (loading || error) {
      return;
    }
    if (tickets.length === 0) {
      if (itemId) {
        navigate(workspacePath(business.id, "tickets"), { replace: true });
      }
      return;
    }
    const exists = tickets.some((item) => item.id === itemId);
    if (!exists) {
      if (itemId) {
        navigate(workspacePath(business.id, "tickets"), { replace: true });
        return;
      }
      if (isDesktop && tickets[0]) {
        navigate(workspacePath(business.id, "tickets", tickets[0].id), { replace: true });
      }
    }
  }, [loading, error, tickets, itemId, business.id, navigate, isDesktop]);

  const selected = tickets.find((item) => item.id === itemId);

  return (
    <div className="grid h-full min-h-0 lg:grid-cols-[minmax(240px,360px)_minmax(0,1fr)]">
      <section
        className={cn(
          "min-h-0 overflow-y-auto border-b border-line lg:border-b-0 lg:border-r",
          selected ? "hidden lg:block" : ""
        )}
      >
        <div className="px-4 py-4 sm:px-5">
          <h2 className="text-lg font-bold">Tickets</h2>
          <p className="mt-1 text-sm text-muted">
            Opened automatically when the assistant escalates to a human.
          </p>
        </div>
        {error ? (
          <div className="px-4 sm:px-5">
            <Alert>{error}</Alert>
          </div>
        ) : null}
        {loading ? (
          <p className="px-4 text-sm text-muted sm:px-5">Loading tickets…</p>
        ) : tickets.length === 0 ? (
          <div className="px-4 py-12 text-center sm:px-5">
            <HiOutlineTicket className="mx-auto h-8 w-8 text-muted" />
            <p className="mt-3 font-semibold">No tickets yet</p>
            <p className="mt-1 text-sm text-muted">
              Use Test chat to try a payment failure or “I need a human”.
            </p>
          </div>
        ) : (
          <ul>
            {tickets.map((ticket) => {
              const active = ticket.id === itemId;
              return (
                <li key={ticket.id}>
                  <Link
                    to={workspacePath(business.id, "tickets", ticket.id)}
                    className={cn(
                      "block w-full border-t border-line px-4 py-3.5 text-left text-ink no-underline sm:px-5",
                      active ? "bg-paper" : "hover:bg-paper/70"
                    )}
                    aria-current={active ? "page" : undefined}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-mono text-xs font-bold">{ticket.number}</span>
                      <span
                        className={cn(
                          "rounded-full px-2 py-0.5 text-xs font-bold",
                          PRIORITY_STYLES[ticket.priority] || PRIORITY_STYLES.medium
                        )}
                      >
                        {ticket.priority}
                      </span>
                    </div>
                    <p className="mt-1 truncate font-semibold">{ticket.title}</p>
                    <p className="mt-1 text-xs text-muted">
                      {CATEGORY_LABELS[ticket.category] || ticket.category} ·{" "}
                      {formatDate(ticket.created_at)}
                    </p>
                  </Link>
                </li>
              );
            })}
          </ul>
        )}
      </section>
      <section
        className={cn(
          "min-h-0 overflow-y-auto px-4 py-4 sm:px-6",
          selected ? "" : "hidden lg:block"
        )}
      >
        {!selected ? (
          <p className="text-sm text-muted">Select a ticket to read the conversation.</p>
        ) : (
          <TicketDetail ticket={selected} business={business} />
        )}
      </section>
    </div>
  );
}

function TicketDetail({ ticket, business }) {
  return (
    <div className="mx-auto max-w-2xl">
      <Link
        to={workspacePath(business.id, "tickets")}
        className="mb-4 inline-flex items-center gap-1.5 text-sm font-semibold text-harbor no-underline lg:hidden"
      >
        <HiOutlineArrowLeft className="h-4 w-4" />
        All tickets
      </Link>
      <p className="font-mono text-sm font-bold">{ticket.number}</p>
      <h2 className="mt-1 text-xl font-bold">{ticket.title}</h2>
      <p className="mt-2 text-sm leading-relaxed text-muted">{ticket.summary}</p>
      <dl className="mt-4 grid gap-2 text-sm sm:grid-cols-2">
        <Info label="Category" className="capitalize">
          {CATEGORY_LABELS[ticket.category] || ticket.category}
        </Info>
        <Info label="Priority" className="capitalize">
          {ticket.priority}
        </Info>
        <Info label="Status" className="capitalize">
          {ticket.status}
        </Info>
        <Info label="Notification" className="capitalize">
          {ticket.email_status || "—"}
        </Info>
        <Info label="Customer email">
          {ticket.customer_email ? (
            <a
              href={`mailto:${ticket.customer_email}`}
              className="break-all text-harbor underline underline-offset-2"
            >
              {ticket.customer_email}
            </a>
          ) : (
            "—"
          )}
        </Info>
        <Info label="Customer phone">
          {ticket.customer_phone ? (
            <a
              href={`tel:${telHref(ticket.customer_phone)}`}
              className="text-harbor underline underline-offset-2"
            >
              {ticket.customer_phone}
            </a>
          ) : (
            "—"
          )}
        </Info>
      </dl>
      {ticket.internal_reason ? (
        <div className="mt-5 rounded-xl bg-paper px-4 py-3">
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-muted">
            Why it was escalated
          </p>
          <p className="mt-2 text-sm leading-relaxed">{ticket.internal_reason}</p>
        </div>
      ) : null}
      {ticket.email_error ? (
        <p className="mt-3 text-sm text-red-800">{ticket.email_error}</p>
      ) : null}
      <div className="mt-6">
        <h3 className="text-sm font-bold">Conversation</h3>
        <ul className="mt-3 grid gap-3">
          {(ticket.messages || []).map((item, index) => (
            <li
              key={`${item.role}-${index}`}
              className={cn(
                "rounded-2xl px-3.5 py-3 text-sm leading-relaxed",
                item.role === "user" ? "bg-harbor text-paper" : "bg-paper text-ink"
              )}
            >
              <p className="mb-1 text-xs font-bold uppercase tracking-wide opacity-70">
                {item.role}
              </p>
              <p className="whitespace-pre-wrap break-words">{item.content}</p>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function Info({ label, children, className }) {
  return (
    <div>
      <dt className="text-xs font-bold uppercase tracking-[0.14em] text-muted">{label}</dt>
      <dd className={cn("mt-1", className)}>{children}</dd>
    </div>
  );
}

function telHref(phone) {
  const digits = String(phone).replace(/\D/g, "");
  return String(phone).trim().startsWith("+") ? `+${digits}` : digits;
}

function isDesktopViewport() {
  return typeof window !== "undefined" && window.matchMedia("(min-width: 1024px)").matches;
}

function useIsDesktop() {
  const [isDesktop, setIsDesktop] = useState(isDesktopViewport);

  useEffect(() => {
    const media = window.matchMedia("(min-width: 1024px)");
    function onChange() {
      setIsDesktop(media.matches);
    }
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, []);

  return isDesktop;
}

function formatDate(value) {
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}
