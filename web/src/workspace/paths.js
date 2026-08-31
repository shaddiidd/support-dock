export const DEFAULT_TAB = "documents";

export const WORKSPACE_TABS = ["documents", "tickets", "assistant", "chat"];

const TAB_KEY = "sd_active_tab";

export function isWorkspaceTab(value) {
  return WORKSPACE_TABS.includes(value);
}

export function workspacePath(businessId, tab = DEFAULT_TAB, itemId) {
  const safeTab = isWorkspaceTab(tab) ? tab : DEFAULT_TAB;
  const id = encodeURIComponent(String(businessId));
  if (itemId && safeTab === "tickets") {
    return `/${id}/${safeTab}/${encodeURIComponent(String(itemId))}`;
  }
  return `/${id}/${safeTab}`;
}

export function rememberTab(tab) {
  if (isWorkspaceTab(tab)) {
    localStorage.setItem(TAB_KEY, tab);
  }
}

export function rememberedTab() {
  const value = localStorage.getItem(TAB_KEY);
  return isWorkspaceTab(value) ? value : DEFAULT_TAB;
}
