/**
 * Axios instance with JWT bearer + refresh interceptor.
 *
 * - Access token is added to every request.
 * - A single 401 per request triggers a refresh attempt; on success the original
 *   request is retried with the new access token. On failure the auth store is
 *   cleared and the user is redirected to /login.
 * - Concurrent 401s are coalesced via a shared refresh promise so we only hit
 *   /auth/refresh/ once.
 *
 * Mirrors `yangi-mahalla-main/src/libs/axios.js` from the legacy project, adapted
 * to Vue 3 + TypeScript (native axios v1 API, no `@core/auth/jwt` wrapper).
 */
import axios, {
  AxiosError,
  type AxiosInstance,
  type AxiosRequestConfig,
  type InternalAxiosRequestConfig,
} from "axios"

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1"

export const http: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 30_000,
  headers: { "Content-Type": "application/json" },
})

// --- Token storage (module-local so we can import here without a circular dep on the store) ---

const ACCESS_KEY = "rcrm.access"
const REFRESH_KEY = "rcrm.refresh"

export const tokenStore = {
  getAccess: () => localStorage.getItem(ACCESS_KEY),
  getRefresh: () => localStorage.getItem(REFRESH_KEY),
  set: (access: string, refresh: string) => {
    localStorage.setItem(ACCESS_KEY, access)
    localStorage.setItem(REFRESH_KEY, refresh)
  },
  clear: () => {
    localStorage.removeItem(ACCESS_KEY)
    localStorage.removeItem(REFRESH_KEY)
  },
}

// --- Request interceptor: attach access token ---

http.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const access = tokenStore.getAccess()
  if (access && config.headers) {
    config.headers.Authorization = `Bearer ${access}`
  }
  return config
})

// --- Response interceptor: refresh on 401 ---

type Retryable = AxiosRequestConfig & { _retried?: boolean }

let refreshPromise: Promise<string> | null = null

async function refreshAccessToken(): Promise<string> {
  const refresh = tokenStore.getRefresh()
  if (!refresh) throw new Error("no refresh token")

  // Bypass interceptors with a raw axios call.
  const { data } = await axios.post<{ access: string; refresh?: string }>(
    `${BASE_URL}/auth/refresh/`,
    { refresh },
  )
  tokenStore.set(data.access, data.refresh ?? refresh)
  return data.access
}

http.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as Retryable | undefined
    const status = error.response?.status

    if (status === 401 && original && !original._retried) {
      original._retried = true
      try {
        refreshPromise ??= refreshAccessToken().finally(() => {
          refreshPromise = null
        })
        const newAccess = await refreshPromise
        if (original.headers) original.headers.Authorization = `Bearer ${newAccess}`
        return http.request(original)
      } catch {
        tokenStore.clear()
        // Hard redirect — avoids circular import into the router module.
        if (typeof window !== "undefined" && window.location.pathname !== "/login") {
          window.location.href = "/login"
        }
      }
    }

    return Promise.reject(error)
  },
)
