const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000"

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
  const res = await fetch(`${API_BASE}/api/codes?${search}`)
  return res.json()
}

export async function fetchStats() {
  const res = await fetch(`${API_BASE}/api/stats`)
  return res.json()
}

export async function redeemCode(codeId: number, accountId?: number) {
  const res = await fetch(`${API_BASE}/api/redeem`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code_id: codeId, account_id: accountId }),
  })
  return res.json()
}

export async function skipCode(codeId: number) {
  const res = await fetch(`${API_BASE}/api/codes/${codeId}/skip`, {
    method: "POST",
  })
  return res.json()
}

export async function validateCode(codeId: number) {
  const res = await fetch(`${API_BASE}/api/validate/${codeId}`, {
    method: "POST",
  })
  return res.json()
}

export async function autoEnterGiveaway(url: string, title?: string) {
  const res = await fetch(`${API_BASE}/api/auto-enter`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, title }),
  })
  return res.json()
}

export async function configureReddit(config: {
  client_id: string
  client_secret: string
  user_agent: string
}) {
  const res = await fetch(`${API_BASE}/api/config/reddit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  })
  return res.json()
}

export async function configureSteam(cookies: Record<string, string>, name?: string) {
  const res = await fetch(`${API_BASE}/api/config/steam-session`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ cookies, account_name: name || "default" }),
  })
  return res.json()
}

export async function createAccount(name: string, cookies: Record<string, string>) {
  const res = await fetch(`${API_BASE}/api/accounts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, cookies }),
  })
  return res.json()
}

export async function fetchAccounts() {
  const res = await fetch(`${API_BASE}/api/accounts`)
  return res.json()
}

export async function toggleAccount(id: number) {
  const res = await fetch(`${API_BASE}/api/accounts/${id}/toggle`, { method: "POST" })
  return res.json()
}

export async function deleteAccount(id: number) {
  const res = await fetch(`${API_BASE}/api/accounts/${id}`, { method: "DELETE" })
  return res.json()
}

export async function fetchNotificationConfig() {
  const res = await fetch(`${API_BASE}/api/config/notifications`)
  return res.json()
}

export async function updateNotificationConfig(config: {
  discord_webhook_url?: string
  telegram_bot_token?: string
  telegram_chat_id?: string
  notify_on_new?: boolean
  notify_on_redeem?: boolean
  notify_on_fail?: boolean
}) {
  const res = await fetch(`${API_BASE}/api/config/notifications`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  })
  return res.json()
}

export function getWsUrl() {
  return API_BASE.replace(/^http/, "ws") + "/ws"
}

export function getExportUrl(format: "json" | "csv", status?: string, code_type?: string) {
  const search = new URLSearchParams()
  if (status) search.set("status", status)
  if (code_type) search.set("code_type", code_type)
  const qs = search.toString()
  return `${API_BASE}/api/export/${format}${qs ? "?" + qs : ""}`
}

export async function fetchASFConfig() {
  const res = await fetch(`${API_BASE}/api/config/asf`)
  return res.json()
}

export async function updateASFConfig(config: {
  ipc_url: string
  ipc_password: string
  default_bot: string
  auto_redeem: boolean
}) {
  const res = await fetch(`${API_BASE}/api/config/asf`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  })
  return res.json()
}

export async function fetchASFBots() {
  const res = await fetch(`${API_BASE}/api/asf/bots`)
  return res.json()
}

export async function asfRedeemCode(codeId: number, bot?: string) {
  const res = await fetch(`${API_BASE}/api/asf/redeem`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code_id: codeId, bot }),
  })
  return res.json()
}

export async function asfRedeemAll(bot?: string) {
  const res = await fetch(`${API_BASE}/api/asf/redeem-all?${bot ? `bot=${bot}` : ""}`, {
    method: "POST",
  })
  return res.json()
}

export async function asfRetryFailed(bot?: string) {
  const res = await fetch(`${API_BASE}/api/asf/retry-failed?${bot ? `bot=${bot}` : ""}`, {
    method: "POST",
  })
  return res.json()
}

export async function triggerScrape() {
  const res = await fetch(`${API_BASE}/api/scrape`, { method: "POST" })
  return res.json()
}
