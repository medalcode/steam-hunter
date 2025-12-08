import { useState } from "react"
import { configureReddit, configureSteam, fetchAccounts } from "../api/client"
import type { SteamAccount } from "../types"

interface Props {
  onClose: () => void
}

export function ConfigModal({ onClose }: Props) {
  const [tab, setTab] = useState<"reddit" | "steam">("reddit")
  const [message, setMessage] = useState<string | null>(null)
  const [accounts, setAccounts] = useState<SteamAccount[]>([])

  const [redditForm, setRedditForm] = useState({
    client_id: "",
    client_secret: "",
    user_agent: "steam-hunter/1.0",
  })

  const [steamCookies, setSteamCookies] = useState("")

  const handleRedditSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setMessage(null)
    const result = await configureReddit(redditForm)
    setMessage(
      `Reddit configured! Found ${result.test_results} test posts.`,
    )
  }

  const handleSteamSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setMessage(null)
    try {
      const parsed: Record<string, string> = {}
      for (const line of steamCookies.trim().split("\n")) {
        const [key, ...rest] = line.split("=")
        if (key && rest.length) {
          parsed[key.trim()] = rest.join("=").trim()
        }
      }
      await configureSteam(parsed)
      setMessage("Steam account configured!")
      loadAccounts()
    } catch {
      setMessage("Invalid cookie format")
    }
  }

  const loadAccounts = async () => {
    const data = await fetchAccounts()
    setAccounts(data)
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
            Reddit API
          </button>
          <button
            className={`tab ${tab === "steam" ? "active" : ""}`}
            onClick={() => {
              setTab("steam")
              loadAccounts()
            }}
          >
            Steam Session
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
              <a
                href="https://www.reddit.com/prefs/apps"
                target="_blank"
                rel="noopener noreferrer"
              >
                reddit.com/prefs/apps
              </a>
            </p>
            <label>
              Client ID:
              <input
                value={redditForm.client_id}
                onChange={(e) =>
                  setRedditForm((f) => ({ ...f, client_id: e.target.value }))
                }
                placeholder="..."
              />
            </label>
            <label>
              Client Secret:
              <input
                value={redditForm.client_secret}
                onChange={(e) =>
                  setRedditForm((f) => ({
                    ...f,
                    client_secret: e.target.value,
                  }))
                }
                placeholder="..."
              />
            </label>
            <button type="submit" className="btn">
              Save Reddit
            </button>
          </form>
        )}

        {tab === "steam" && (
          <form onSubmit={handleSteamSubmit}>
            <p className="hint">
              Export cookies from{" "}
              <code>store.steampowered.com</code> in your browser (one{" "}
              <code>key=value</code> per line). Includes{" "}
              <code>steamLogin</code>, <code>sessionid</code>,{" "}
              <code>steampowered_sesh</code>.
            </p>
            <label>
              Cookies:
              <textarea
                value={steamCookies}
                onChange={(e) => setSteamCookies(e.target.value)}
                rows={8}
                placeholder="steamLogin=7656119...&#10;sessionid=abc123...&#10;steampowered_sesh=..."
              />
            </label>
            <button type="submit" className="btn">
              Save Steam Session
            </button>
          </form>
        )}

        {accounts.length > 0 && (
          <section className="account-list">
            <h3>Configured Accounts</h3>
            {accounts.map((a) => (
              <div key={a.id} className="account-item">
                <span>{a.name}</span>
                <span className={a.has_cookies ? "text-green" : "text-red"}>
                  {a.has_cookies ? "Cookies set" : "No cookies"}
                </span>
              </div>
            ))}
          </section>
        )}
      </div>
    </div>
  )
}
