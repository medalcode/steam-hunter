import { useState, useEffect } from "react"
import {
  configureReddit,
  configureSteam,
  fetchAccounts,
  createAccount,
  toggleAccount,
  deleteAccount,
  fetchNotificationConfig,
  updateNotificationConfig,
} from "../api/client"
import type { SteamAccount } from "../types"

interface Props {
  onClose: () => void
}

export function ConfigModal({ onClose }: Props) {
  const [tab, setTab] = useState<"reddit" | "steam" | "notifications">("reddit")
  const [message, setMessage] = useState<string | null>(null)
  const [accounts, setAccounts] = useState<SteamAccount[]>([])

  const [redditForm, setRedditForm] = useState({
    client_id: "",
    client_secret: "",
    user_agent: "steam-hunter/1.0",
  })

  const [steamCookies, setSteamCookies] = useState("")
  const [steamAcctName, setSteamAcctName] = useState("default")
  const [newAcctName, setNewAcctName] = useState("")
  const [newAcctCookies, setNewAcctCookies] = useState("")

  const [notifForm, setNotifForm] = useState({
    discord_webhook_url: "",
    telegram_bot_token: "",
    telegram_chat_id: "",
    notify_on_new: true,
    notify_on_redeem: false,
    notify_on_fail: true,
  })

  const loadAccounts = async () => {
    const data = await fetchAccounts()
    setAccounts(data)
  }

  const loadNotifConfig = async () => {
    try {
      const data = await fetchNotificationConfig()
      setNotifForm(data)
    } catch {
      /* ignore */
    }
  }

  useEffect(() => {
    if (tab === "steam") loadAccounts()
    if (tab === "notifications") loadNotifConfig()
  }, [tab])

  const showMsg = (msg: string) => {
    setMessage(msg)
    setTimeout(() => setMessage(null), 5000)
  }

  const handleRedditSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const result = await configureReddit(redditForm)
    showMsg(`Reddit configured! Found ${result.test_results} test posts.`)
  }

  const handleSteamSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const parsed: Record<string, string> = {}
      for (const line of steamCookies.trim().split("\n")) {
        const [key, ...rest] = line.split("=")
        if (key && rest.length) {
          parsed[key.trim()] = rest.join("=").trim()
        }
      }
      await configureSteam(parsed, steamAcctName)
      showMsg("Steam account configured!")
      loadAccounts()
      setSteamCookies("")
    } catch {
      showMsg("Invalid cookie format")
    }
  }

  const handleCreateAccount = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const parsed: Record<string, string> = {}
      for (const line of newAcctCookies.trim().split("\n")) {
        const [key, ...rest] = line.split("=")
        if (key && rest.length) {
          parsed[key.trim()] = rest.join("=").trim()
        }
      }
      await createAccount(newAcctName, parsed)
      showMsg(`Account '${newAcctName}' created!`)
      loadAccounts()
      setNewAcctName("")
      setNewAcctCookies("")
    } catch {
      showMsg("Invalid cookie format")
    }
  }

  const handleToggleAccount = async (id: number) => {
    await toggleAccount(id)
    loadAccounts()
  }

  const handleDeleteAccount = async (id: number, name: string) => {
    if (!confirm(`Delete account '${name}'?`)) return
    await deleteAccount(id)
    showMsg(`Account '${name}' deleted`)
    loadAccounts()
  }

  const handleNotifSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    await updateNotificationConfig(notifForm)
    showMsg("Notification config saved!")
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Configuration</h2>
          <button className="btn-close" onClick={onClose}>
            &times;
          </button>
        </div>

        <div className="tabs">
          <button
            className={`tab ${tab === "reddit" ? "active" : ""}`}
            onClick={() => setTab("reddit")}
          >
            Reddit
          </button>
          <button
            className={`tab ${tab === "steam" ? "active" : ""}`}
            onClick={() => setTab("steam")}
          >
            Steam Accts
          </button>
          <button
            className={`tab ${tab === "notifications" ? "active" : ""}`}
            onClick={() => setTab("notifications")}
          >
            Notifications
          </button>
        </div>

        {message && (
          <div className="message" onClick={() => setMessage(null)}>
            {message}
          </div>
        )}

        {tab === "reddit" && (
          <form onSubmit={handleRedditSubmit}>
            <p className="hint">
              Create a Reddit app at{" "}
              <a href="https://www.reddit.com/prefs/apps" target="_blank" rel="noopener noreferrer">
                reddit.com/prefs/apps
              </a>
            </p>
            <label>
              Client ID:
              <input
                value={redditForm.client_id}
                onChange={(e) => setRedditForm((f) => ({ ...f, client_id: e.target.value }))}
                placeholder="..."
              />
            </label>
            <label>
              Client Secret:
              <input
                value={redditForm.client_secret}
                onChange={(e) => setRedditForm((f) => ({ ...f, client_secret: e.target.value }))}
                placeholder="..."
              />
            </label>
            <button type="submit" className="btn">
              Save Reddit
            </button>
          </form>
        )}

        {tab === "steam" && (
          <div>
            <form onSubmit={handleSteamSubmit}>
              <h3>Update existing account</h3>
              <label>
                Account name:
                <input
                  value={steamAcctName}
                  onChange={(e) => setSteamAcctName(e.target.value)}
                  placeholder="default"
                />
              </label>
              <label>
                Cookies (key=value per line):
                <textarea
                  value={steamCookies}
                  onChange={(e) => setSteamCookies(e.target.value)}
                  rows={6}
                  placeholder="steamLogin=7656119..."
                />
              </label>
              <button type="submit" className="btn">
                Save
              </button>
            </form>

            <hr className="divider" />

            <form onSubmit={handleCreateAccount}>
              <h3>Add new account</h3>
              <label>
                Name:
                <input
                  value={newAcctName}
                  onChange={(e) => setNewAcctName(e.target.value)}
                  placeholder="alt-account"
                />
              </label>
              <label>
                Cookies (key=value per line):
                <textarea
                  value={newAcctCookies}
                  onChange={(e) => setNewAcctCookies(e.target.value)}
                  rows={6}
                  placeholder="steamLogin=7656119..."
                />
              </label>
              <button type="submit" className="btn">
                Add Account
              </button>
            </form>

            {accounts.length > 0 && (
              <section className="account-list">
                <h3>Configured Accounts</h3>
                {accounts.map((a) => (
                  <div key={a.id} className="account-item">
                    <div>
                      <strong>{a.name}</strong>
                      <span className={a.has_cookies ? "text-green" : "text-red"}>
                        {" "}{a.has_cookies ? "cookies set" : "no cookies"}
                      </span>
                      <span className="text-muted"> (active: {a.is_active ? "yes" : "no"})</span>
                    </div>
                    <div className="acct-actions">
                      <button className="btn btn-xs btn-outline" onClick={() => handleToggleAccount(a.id)}>
                        {a.is_active ? "Deactivate" : "Activate"}
                      </button>
                      <button className="btn btn-xs btn-danger" onClick={() => handleDeleteAccount(a.id, a.name)}>
                        Delete
                      </button>
                    </div>
                  </div>
                ))}
              </section>
            )}
          </div>
        )}

        {tab === "notifications" && (
          <form onSubmit={handleNotifSubmit}>
            <h3>Discord</h3>
            <label>
              Webhook URL:
              <input
                value={notifForm.discord_webhook_url}
                onChange={(e) => setNotifForm((f) => ({ ...f, discord_webhook_url: e.target.value }))}
                placeholder="https://discord.com/api/webhooks/..."
              />
            </label>

            <h3>Telegram</h3>
            <label>
              Bot Token:
              <input
                value={notifForm.telegram_bot_token}
                onChange={(e) => setNotifForm((f) => ({ ...f, telegram_bot_token: e.target.value }))}
                placeholder="123456:ABC-DEF..."
              />
            </label>
            <label>
              Chat ID:
              <input
                value={notifForm.telegram_chat_id}
                onChange={(e) => setNotifForm((f) => ({ ...f, telegram_chat_id: e.target.value }))}
                placeholder="-100123456789"
              />
            </label>

            <h3>Notify on</h3>
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={notifForm.notify_on_new}
                onChange={(e) => setNotifForm((f) => ({ ...f, notify_on_new: e.target.checked }))}
              />
              New codes found
            </label>
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={notifForm.notify_on_redeem}
                onChange={(e) => setNotifForm((f) => ({ ...f, notify_on_redeem: e.target.checked }))}
              />
              Code redeemed
            </label>
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={notifForm.notify_on_fail}
                onChange={(e) => setNotifForm((f) => ({ ...f, notify_on_fail: e.target.checked }))}
              />
              Redeem failed
            </label>

            <button type="submit" className="btn">
              Save Notifications
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
