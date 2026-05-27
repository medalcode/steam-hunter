import { useEffect, useState, useRef, useCallback } from "react"
import type { Stats } from "../types"
import { fetchStats, getWsUrl, getExportUrl } from "../api/client"
import { CodeTable } from "./CodeTable"
import { ConfigModal } from "./ConfigModal"

export function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [filter, setFilter] = useState({ status: "new", code_type: "" })
  const [showConfig, setShowConfig] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)
  const [toast, setToast] = useState<string | null>(null)
  const wsRef = useRef<WebSocket | null>(null)

  const loadStats = useCallback(async () => {
    try {
      const data = await fetchStats()
      setStats(data)
    } catch {
      /* ignore */
    }
  }, [])

  useEffect(() => {
    loadStats()
    const interval = setInterval(loadStats, 60000)
    return () => clearInterval(interval)
  }, [loadStats])

  useEffect(() => {
    setRefreshKey((k) => k + 1)
  }, [filter])

  useEffect(() => {
    let reconnectTimer: ReturnType<typeof setTimeout>
    let closed = false

    function connect() {
      const ws = new WebSocket(getWsUrl())
      wsRef.current = ws

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)
          if (msg.type === "new_codes") {
            setToast(`\u2728 ${msg.count} new codes found!`)
            loadStats()
            setRefreshKey((k) => k + 1)
          }
        } catch {
          /* ignore */
        }
      }

      ws.onclose = () => {
        wsRef.current = null
        if (!closed) {
          reconnectTimer = setTimeout(connect, 5000)
        }
      }

      ws.onerror = () => {
        ws.close()
      }
    }

    connect()
    return () => {
      closed = true
      clearTimeout(reconnectTimer)
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [loadStats])

  useEffect(() => {
    if (toast) {
      const t = setTimeout(() => setToast(null), 5000)
      return () => clearTimeout(t)
    }
  }, [toast])

  return (
    <div className="dashboard">
      <header>
        <h1>Steam Hunter</h1>
        <div className="header-actions">
          <div className="dropdown">
            <button className="btn">Export</button>
            <div className="dropdown-content">
              <a href={getExportUrl("json", filter.status || undefined, filter.code_type || undefined)} download>Export JSON</a>
              <a href={getExportUrl("csv", filter.status || undefined, filter.code_type || undefined)} download>Export CSV</a>
            </div>
          </div>
          <button className="btn" onClick={() => setShowConfig(true)}>
            Config
          </button>
        </div>
      </header>

      {toast && <div className="toast" onClick={() => setToast(null)}>{toast}</div>}

      {stats && (
        <section className="stats">
          <div className="stat-card new">
            <span className="stat-value">{stats.new}</span>
            <span className="stat-label">New</span>
          </div>
          <div className="stat-card redeemed">
            <span className="stat-value">{stats.redeemed}</span>
            <span className="stat-label">Redeemed</span>
          </div>
          <div className="stat-card failed">
            <span className="stat-value">{stats.failed}</span>
            <span className="stat-label">Failed</span>
          </div>
          <div className="stat-card expired">
            <span className="stat-value">{stats.expired}</span>
            <span className="stat-label">Expired</span>
          </div>
          <div className="stat-card total">
            <span className="stat-value">{stats.total}</span>
            <span className="stat-label">Total</span>
          </div>
        </section>
      )}

      <section className="filters">
        <label>
          Status:
          <select
            value={filter.status}
            onChange={(e) => setFilter((f) => ({ ...f, status: e.target.value }))}
          >
            <option value="">All</option>
            <option value="new">New</option>
            <option value="redeemed">Redeemed</option>
            <option value="failed">Failed</option>
            <option value="expired">Expired</option>
          </select>
        </label>
        <label>
          Type:
          <select
            value={filter.code_type}
            onChange={(e) => setFilter((f) => ({ ...f, code_type: e.target.value }))}
          >
            <option value="">All</option>
            <option value="key">Steam Key</option>
            <option value="gift_link">Gift Link</option>
            <option value="giveaway">Giveaway</option>
          </select>
        </label>
      </section>

      <CodeTable
        key={refreshKey}
        status={filter.status || undefined}
        codeType={filter.code_type || undefined}
      />

      {showConfig && <ConfigModal onClose={() => setShowConfig(false)} />}
    </div>
  )
}
