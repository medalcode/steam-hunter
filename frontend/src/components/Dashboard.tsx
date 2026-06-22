import { useEffect, useState, useRef, useCallback, useMemo, lazy, Suspense } from "react"
import type { Stats } from "../types"
import { fetchStats, getWsUrl, getExportUrl, asfRedeemAll, fetchASFBots } from "../api/client"
import { CodeTable } from "./CodeTable"

const ConfigModal = lazy(() => import("./ConfigModal").then(m => ({ default: m.ConfigModal })))

export function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [filter, setFilter] = useState({ status: "new", code_type: "" })
  const [showConfig, setShowConfig] = useState(false)
  const [toast, setToast] = useState<{ id: number; message: string } | null>(null)
  const [asfBots, setAsfBots] = useState<string[]>([])
  const [redeemingAll, setRedeemingAll] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const toastIdRef = useRef(0)

  const showToast = useCallback((msg: string) => {
    const id = ++toastIdRef.current
    setToast({ id, message: msg })
  }, [])

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
    fetchASFBots().then(bots => setAsfBots(bots.map((b: { name: string }) => b.name))).catch(() => {})
    const interval = setInterval(loadStats, 60000)
    return () => clearInterval(interval)
  }, [loadStats])

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
            showToast(`\u2728 ${msg.count} new codes found!`)
            loadStats()
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
  }, [loadStats, showToast])

  useEffect(() => {
    if (toast) {
      const id = toast.id
      const t = setTimeout(() => {
        setToast(prev => prev?.id === id ? null : prev)
      }, 5000)
      return () => clearTimeout(t)
    }
  }, [toast])

  const handleRedeemAll = async () => {
    setRedeemingAll(true)
    try {
      const result = await asfRedeemAll()
      showToast(`\u2728 Redeemed ${result.results?.filter((r: { success: boolean }) => r.success).length || 0} keys`)
      loadStats()
    } catch {
      showToast("\u274c Bulk redeem failed")
    }
    setRedeemingAll(false)
  }

  const exportUrlJson = useMemo(
    () => getExportUrl("json", filter.status || undefined, filter.code_type || undefined),
    [filter.status, filter.code_type]
  )
  const exportUrlCsv = useMemo(
    () => getExportUrl("csv", filter.status || undefined, filter.code_type || undefined),
    [filter.status, filter.code_type]
  )

  return (
    <div className="dashboard">
      <header>
        <h1>Steam Hunter</h1>
        <div className="header-actions">
          {asfBots.length > 0 && (
            <button
              className="btn btn-asf"
              onClick={handleRedeemAll}
              disabled={redeemingAll}
              title="Redeem all pending keys via ASF"
            >
              {redeemingAll ? "..." : `Redeem All (${stats?.new || 0})`}
            </button>
          )}
          <div className="dropdown">
            <button className="btn">Export</button>
            <div className="dropdown-content">
              <a href={exportUrlJson} download>Export JSON</a>
              <a href={exportUrlCsv} download>Export CSV</a>
            </div>
          </div>
          <button className="btn" onClick={() => setShowConfig(true)}>
            Config
          </button>
        </div>
      </header>

      {toast && <div className="toast" onClick={() => setToast(null)}>{toast.message}</div>}

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
        status={filter.status || undefined}
        codeType={filter.code_type || undefined}
      />

      {showConfig && (
        <Suspense fallback={<div>Loading configuration...</div>}>
          <ConfigModal onClose={() => setShowConfig(false)} />
        </Suspense>
      )}
    </div>
  )
}
