export interface FoundCode {
  id: number
  code: string
  code_type: "key" | "gift_link" | "giveaway"
  source: string
  source_url: string | null
  title: string | null
  status: "new" | "redeemed" | "failed" | "expired" | "retry"
  found_at: string | null
  redeemed_at: string | null
  error_message: string | null
  validation_status?: string | null
  validation_reason?: string | null
  steam_account_id?: number | null
}

export interface Stats {
  total: number
  new: number
  redeemed: number
  expired: number
  failed: number
  by_type: Record<string, number>
}

export interface SteamAccount {
  id: number
  name: string
  is_active: boolean
  has_cookies: boolean
  created_at: string
}

export interface SearchSource {
  id: number
  name: string
  source_type: string
  enabled: boolean
  last_checked: string | null
  interval_minutes: number
}

export interface ASFConfig {
  ipc_url: string
  ipc_password: boolean
  default_bot: string
  auto_redeem: boolean
}

export interface ASFBot {
  name: string
  status: string
  games: number
  online: boolean
}

export interface ASFRedeemResult {
  key: string
  success: boolean
  status: string
  message: string
}
