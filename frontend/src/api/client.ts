const API_BASE = ""

function getApiKey(): string {
  try {
    return sessionStorage.getItem("steam_hunter_api_key") || ""
  } catch {
    return ""
  }
}

async function request<T>(url: string, options?: RequestInit, timeout = 30000): Promise<T> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeout)

  const headers: Record<string, string> = {
    ...(options?.headers as Record<string, string> || {}),
  }
  const apiKey = getApiKey()
  if (apiKey) {
    headers["Authorization"] = `Bearer ${apiKey}`
  }

  try {
    const res = await fetch(url, { ...options, headers, signal: controller.signal })
    if (!res.ok) {
      const body = await res.text()
      throw new Error(`HTTP ${res.status}: ${body.slice(0, 200)}`)
    }
    return res.json()
  } finally {
    clearTimeout(timer)
  }
}

export function setApiKey(key: string) {
  sessionStorage.setItem("steam_hunter_api_key", key)
}

export async function fetchCodes(params?: {
  status?: string
  code_type?: string
  source?: string
  limit?: number
}) {
  const search = new URLSearchParams()
  if (params?.status) search.set("status", params.status)
  if (params?.code_type) search.set("code_type", params.code_type)
  if (params?.source) search.set("source", params.source)
  if (params?.limit) search.set("limit", String(params.limit))
  return request(`${API_BASE}/api/codes?${search}`)
}

export async function fetchStats() {
  return request(`${API_BASE}/api/stats`)
}

export async function redeemCode(codeId: number, accountId?: number) {
  return request(`${API_BASE}/api/redeem`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code_id: codeId, account_id: accountId }),
  })
}

export async function skipCode(codeId: number) {
  return request(`${API_BASE}/api/codes/${codeId}/skip`, {
    method: "POST",
  })
}

export async function validateCode(codeId: number) {
  return request(`${API_BASE}/api/validate/${codeId}`, {
    method: "POST",
  })
}

export async function autoEnterGiveaway(url: string, title?: string) {
  return request(`${API_BASE}/api/auto-enter`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, title }),
  })
}

export async function configureReddit(config: {
  client_id: string
  client_secret: string
  user_agent: string
}) {
  return request(`${API_BASE}/api/config/reddit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  })
}

export async function configureSteam(cookies: Record<string, string>, name?: string) {
  return request(`${API_BASE}/api/config/steam-session`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ cookies, account_name: name || "default" }),
  })
}

export async function createAccount(name: string, cookies: Record<string, string>) {
  return request(`${API_BASE}/api/accounts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, cookies }),
  })
}

export async function fetchAccounts() {
  return request(`${API_BASE}/api/accounts`)
}

export async function toggleAccount(id: number) {
  return request(`${API_BASE}/api/accounts/${id}/toggle`, { method: "POST" })
}

export async function deleteAccount(id: number) {
  return request(`${API_BASE}/api/accounts/${id}`, { method: "DELETE" })
}

export async function fetchNotificationConfig() {
  return request(`${API_BASE}/api/config/notifications`)
}

export async function updateNotificationConfig(config: {
  discord_webhook_url?: string
  telegram_bot_token?: string
  telegram_chat_id?: string
  notify_on_new?: boolean
  notify_on_redeem?: boolean
  notify_on_fail?: boolean
}) {
  return request(`${API_BASE}/api/config/notifications`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  })
}

export function getWsUrl() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:"
  const apiKey = getApiKey()
  return `${protocol}//${window.location.host}/ws${apiKey ? `?token=${encodeURIComponent(apiKey)}` : ""}`
}

export function getExportUrl(format: "json" | "csv", status?: string, code_type?: string) {
  const search = new URLSearchParams()
  if (status) search.set("status", status)
  if (code_type) search.set("code_type", code_type)
  const qs = search.toString()
  return `${API_BASE}/api/export/${format}${qs ? "?" + qs : ""}`
}

export async function fetchASFConfig() {
  return request(`${API_BASE}/api/config/asf`)
}

export async function updateASFConfig(config: {
  ipc_url: string
  ipc_password: string
  default_bot: string
  auto_redeem: boolean
}) {
  return request(`${API_BASE}/api/config/asf`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  })
}

export async function fetchASFBots() {
  return request(`${API_BASE}/api/asf/bots`)
}

export async function asfRedeemCode(codeId: number, bot?: string) {
  return request(`${API_BASE}/api/asf/redeem`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code_id: codeId, bot }),
  })
}

export async function asfRedeemAll(bot?: string) {
  return request(`${API_BASE}/api/asf/redeem-all?${bot ? `bot=${bot}` : ""}`, {
    method: "POST",
  })
}

export async function asfRetryFailed(bot?: string) {
  return request(`${API_BASE}/api/asf/retry-failed?${bot ? `bot=${bot}` : ""}`, {
    method: "POST",
  })
}

export async function triggerScrape() {
  return request(`${API_BASE}/api/scrape`, { method: "POST" })
}
