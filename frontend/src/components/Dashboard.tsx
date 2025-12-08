import { useEffect, useState } from "react"
import type { Stats } from "../types"
import { fetchStats } from "../api/client"
import { CodeTable } from "./CodeTable"
import { ConfigModal } from "./ConfigModal"

export function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [filter, setFilter] = useState<{
    status: string
    code_type: string
  }>({ status: "new", code_type: "" })
  const [showConfig, setShowConfig] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    fetchStats().then(setStats).catch(console.error)
    const interval = setInterval(() => {
      fetchStats().then(setStats).catch(console.error)
    }, 30000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    setRefreshKey((k) => k + 1)
  }, [filter])

  return (
    <div className="dashboard">
      <header>
        <h1>Steam Hunter</h1>
        <div className="header-actions">
          <button className="btn" onClick={() => setShowConfig(true)}>
            Config
          </button>
        </div>
      </header>

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
            onChange={(e) =>
              setFilter((f) => ({ ...f, status: e.target.value }))
            }
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
            onChange={(e) =>
              setFilter((f) => ({ ...f, code_type: e.target.value }))
            }
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
