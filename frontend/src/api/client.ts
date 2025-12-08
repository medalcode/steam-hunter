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

export async function configureSteam(cookies: Record<string, string>) {
  const res = await fetch(`${API_BASE}/api/config/steam-session`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ cookies }),
  })
  return res.json()
}

export async function fetchAccounts() {
  const res = await fetch(`${API_BASE}/api/accounts`)
  return res.json()
}
