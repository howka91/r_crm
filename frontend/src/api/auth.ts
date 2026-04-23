import { http, tokenStore } from "@/libs/axios"
import type { Staff } from "@/types/models"

export interface LoginRequest {
  login: string
  password: string
}

export interface LoginResponse {
  access: string
  refresh: string
  user: Staff
}

export const authApi = {
  login: (payload: LoginRequest) =>
    http.post<LoginResponse>("/auth/login/", payload).then((r) => r.data),

  me: () => http.get<Staff>("/auth/me/").then((r) => r.data),

  /** Blacklist the stored refresh token on the backend. */
  logout: () => {
    const refresh = tokenStore.getRefresh()
    return http.post("/auth/logout/", { refresh }).then((r) => r.data)
  },
}
