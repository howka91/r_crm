/**
 * Contracts domain API client.
 *
 * Routes mirror backend `apps.contracts.urls`:
 *   /contracts/ /contract-templates/ /payment-schedules/ /payments/
 *
 * Custom ViewSet actions on /contracts/:id/ (Phases 5.2 + 5.3):
 *   send-to-wait / approve / sign / request-edit
 *   generate-schedule / generate-pdf
 */
import { http } from "@/libs/axios"
import type {
  Contract,
  ContractTemplate,
  ContractTemplateWrite,
  ContractWrite,
  Payment,
  PaymentSchedule,
  PaymentScheduleWrite,
  PaymentWrite,
} from "@/types/models"

import type { Paginated } from "./references"

export const contractsApi = {
  list: (params?: Record<string, unknown>) =>
    http.get<Paginated<Contract>>("/contracts/", { params }).then((r) => r.data),
  retrieve: (id: number) =>
    http.get<Contract>(`/contracts/${id}/`).then((r) => r.data),
  create: (payload: ContractWrite) =>
    http.post<Contract>("/contracts/", payload).then((r) => r.data),
  update: (id: number, payload: Partial<ContractWrite>) =>
    http.patch<Contract>(`/contracts/${id}/`, payload).then((r) => r.data),
  destroy: (id: number) => http.delete(`/contracts/${id}/`).then((r) => r.data),

  // Workflow transitions (Phase 5.2). Each returns the full Contract payload
  // after the transition; illegal transitions yield HTTP 409 with
  // `{detail, current_action}`.
  sendToWait: (id: number) =>
    http.post<Contract>(`/contracts/${id}/send-to-wait/`).then((r) => r.data),
  approve: (id: number) =>
    http.post<Contract>(`/contracts/${id}/approve/`).then((r) => r.data),
  sign: (id: number) =>
    http.post<Contract>(`/contracts/${id}/sign/`).then((r) => r.data),
  requestEdit: (id: number, reason: string) =>
    http
      .post<Contract>(`/contracts/${id}/request-edit/`, { reason })
      .then((r) => r.data),

  // Utilities. `generate-schedule` returns the rebuilt rows + a count,
  // NOT the Contract — caller must reload schedules/contract separately
  // if the UI depends on derived fields.
  generateSchedule: (id: number) =>
    http
      .post<{ count: number; schedule: PaymentSchedule[] }>(
        `/contracts/${id}/generate-schedule/`,
      )
      .then((r) => r.data),
  generatePdf: (id: number) =>
    http
      .post<{
        contract: Contract
        pdf_url: string
        pdf_size: number
        filled: Record<string, string>
      }>(`/contracts/${id}/generate-pdf/`)
      .then((r) => r.data),
}

export interface UploadedImage {
  url: string
  filename: string
  size: number
  content_type: string
}

export const contractTemplatesApi = {
  list: (params?: Record<string, unknown>) =>
    http
      .get<Paginated<ContractTemplate>>("/contract-templates/", { params })
      .then((r) => r.data),
  retrieve: (id: number) =>
    http.get<ContractTemplate>(`/contract-templates/${id}/`).then((r) => r.data),
  create: (payload: ContractTemplateWrite) =>
    http
      .post<ContractTemplate>("/contract-templates/", payload)
      .then((r) => r.data),
  update: (id: number, payload: Partial<ContractTemplateWrite>) =>
    http
      .patch<ContractTemplate>(`/contract-templates/${id}/`, payload)
      .then((r) => r.data),
  destroy: (id: number) =>
    http.delete(`/contract-templates/${id}/`).then((r) => r.data),

  uploadImage: (file: File) => {
    const fd = new FormData()
    fd.append("file", file)
    return http
      .post<UploadedImage>("/contract-templates/upload-image/", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((r) => r.data)
  },
}

export const paymentSchedulesApi = {
  list: (params?: Record<string, unknown>) =>
    http
      .get<Paginated<PaymentSchedule>>("/payment-schedules/", { params })
      .then((r) => r.data),
  retrieve: (id: number) =>
    http.get<PaymentSchedule>(`/payment-schedules/${id}/`).then((r) => r.data),
  create: (payload: PaymentScheduleWrite) =>
    http
      .post<PaymentSchedule>("/payment-schedules/", payload)
      .then((r) => r.data),
  update: (id: number, payload: Partial<PaymentScheduleWrite>) =>
    http
      .patch<PaymentSchedule>(`/payment-schedules/${id}/`, payload)
      .then((r) => r.data),
  destroy: (id: number) =>
    http.delete(`/payment-schedules/${id}/`).then((r) => r.data),
}

export const paymentsApi = {
  list: (params?: Record<string, unknown>) =>
    http.get<Paginated<Payment>>("/payments/", { params }).then((r) => r.data),
  retrieve: (id: number) =>
    http.get<Payment>(`/payments/${id}/`).then((r) => r.data),
  create: (payload: PaymentWrite) =>
    http.post<Payment>("/payments/", payload).then((r) => r.data),
  update: (id: number, payload: Partial<PaymentWrite>) =>
    http.patch<Payment>(`/payments/${id}/`, payload).then((r) => r.data),
  destroy: (id: number) => http.delete(`/payments/${id}/`).then((r) => r.data),
}
