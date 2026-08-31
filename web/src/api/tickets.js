import { request } from "./client";

export function listTickets(token, businessId) {
  return request(`/api/v1/businesses/${businessId}/tickets`, { token });
}

export function getTicket(token, businessId, ticketId) {
  return request(`/api/v1/businesses/${businessId}/tickets/${ticketId}`, { token });
}
