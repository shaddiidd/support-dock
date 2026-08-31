import { request } from "./client";

export function sendChat(token, businessId, payload) {
  return request(`/api/v1/businesses/${businessId}/chat`, {
    method: "POST",
    token,
    body: payload,
  });
}

export function widgetChatPath(businessId) {
  return `/api/v1/widget/${businessId}/chat`;
}
