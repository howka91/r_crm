/**
 * Clients domain API client.
 *
 * Routes mirror backend `apps.clients.urls`:
 *   /clients/ /client-contacts/ /client-requisites/
 *   /client-statuses/ /client-groups/
 */
import { http } from "@/libs/axios"
import type {
  Client,
  ClientContact,
  ClientContactWrite,
  ClientGroup,
  ClientGroupWrite,
  ClientStatus,
  ClientStatusWrite,
  ClientWrite,
  Requisite,
  RequisiteWrite,
} from "@/types/models"

import type { Paginated } from "./references"

export const clientsApi = {
  list: (params?: Record<string, unknown>) =>
    http.get<Paginated<Client>>("/clients/", { params }).then((r) => r.data),
  retrieve: (id: number) =>
    http.get<Client>(`/clients/${id}/`).then((r) => r.data),
  create: (payload: ClientWrite) =>
    http.post<Client>("/clients/", payload).then((r) => r.data),
  update: (id: number, payload: Partial<ClientWrite>) =>
    http.patch<Client>(`/clients/${id}/`, payload).then((r) => r.data),
  destroy: (id: number) => http.delete(`/clients/${id}/`).then((r) => r.data),
}

export const clientContactsApi = {
  list: (params?: Record<string, unknown>) =>
    http.get<Paginated<ClientContact>>("/client-contacts/", { params }).then((r) => r.data),
  retrieve: (id: number) =>
    http.get<ClientContact>(`/client-contacts/${id}/`).then((r) => r.data),
  create: (payload: ClientContactWrite) =>
    http.post<ClientContact>("/client-contacts/", payload).then((r) => r.data),
  update: (id: number, payload: Partial<ClientContactWrite>) =>
    http.patch<ClientContact>(`/client-contacts/${id}/`, payload).then((r) => r.data),
  destroy: (id: number) =>
    http.delete(`/client-contacts/${id}/`).then((r) => r.data),
}

export const clientRequisitesApi = {
  list: (params?: Record<string, unknown>) =>
    http.get<Paginated<Requisite>>("/client-requisites/", { params }).then((r) => r.data),
  retrieve: (id: number) =>
    http.get<Requisite>(`/client-requisites/${id}/`).then((r) => r.data),
  create: (payload: RequisiteWrite) =>
    http.post<Requisite>("/client-requisites/", payload).then((r) => r.data),
  update: (id: number, payload: Partial<RequisiteWrite>) =>
    http.patch<Requisite>(`/client-requisites/${id}/`, payload).then((r) => r.data),
  destroy: (id: number) =>
    http.delete(`/client-requisites/${id}/`).then((r) => r.data),
}

export const clientStatusesApi = {
  list: (params?: Record<string, unknown>) =>
    http.get<Paginated<ClientStatus>>("/client-statuses/", { params }).then((r) => r.data),
  create: (payload: ClientStatusWrite) =>
    http.post<ClientStatus>("/client-statuses/", payload).then((r) => r.data),
  update: (id: number, payload: Partial<ClientStatusWrite>) =>
    http.patch<ClientStatus>(`/client-statuses/${id}/`, payload).then((r) => r.data),
  destroy: (id: number) =>
    http.delete(`/client-statuses/${id}/`).then((r) => r.data),
}

export const clientGroupsApi = {
  list: (params?: Record<string, unknown>) =>
    http.get<Paginated<ClientGroup>>("/client-groups/", { params }).then((r) => r.data),
  create: (payload: ClientGroupWrite) =>
    http.post<ClientGroup>("/client-groups/", payload).then((r) => r.data),
  update: (id: number, payload: Partial<ClientGroupWrite>) =>
    http.patch<ClientGroup>(`/client-groups/${id}/`, payload).then((r) => r.data),
  destroy: (id: number) =>
    http.delete(`/client-groups/${id}/`).then((r) => r.data),
}
