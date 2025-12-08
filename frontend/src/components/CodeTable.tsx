import { useEffect, useState, useCallback } from "react"
import type { FoundCode } from "../types"
import { fetchCodes, redeemCode, skipCode } from "../api/client"

interface Props {
  status?: string
  codeType?: string
}

export function CodeTable({ status, codeType }: Props) {
  const [codes, setCodes] = useState<FoundCode[]>([])
  const [loading, setLoading] = useState(true)
  const [actionId, setActionId] = useState<number | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await fetchCodes({ status, code_type: codeType })
      setCodes(data)
    } catch (e) {
      console.error(e)
    }
    setLoading(false)
  }, [status, codeType])

  useEffect(() => {
    load()
    const interval = setInterval(load, 30000)
    return () => clearInterval(interval)
  }, [load])

  const handleRedeem = async (code: FoundCode) => {
    setActionId(code.id)
    setMessage(null)
    const result = await redeemCode(code.id)
    setMessage(
      result.success
        ? `Redeemed: ${code.code}`
        : `Failed: ${result.message || "Unknown error"}`,
    )
    setActionId(null)
    load()
  }

  const handleSkip = async (code: FoundCode) => {
    setActionId(code.id)
    await skipCode(code.id)
    setActionId(null)
    load()
  }

  if (loading && codes.length === 0) {
    return <div className="loading">Loading...</div>
  }

  return (
    <div>
      {message && (
        <div className="toast" onClick={() => setMessage(null)}>
          {message}
        </div>
      )}
      <table className="code-table">
        <thead>
          <tr>
            <th>Code</th>
            <th>Type</th>
            <th>Source</th>
            <th>Title</th>
            <th>Status</th>
            <th>Found</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {codes.length === 0 && (
            <tr>
              <td colSpan={7} className="empty">
                No codes found
              </td>
            </tr>
          )}
          {codes.map((code) => (
            <tr key={code.id} className={`status-${code.status}`}>
              <td className="code-cell">
                {code.code_type === "key" ? (
                  <code>{code.code}</code>
                ) : (
                  <a
                    href={code.code}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {code.code.length > 60
                      ? code.code.slice(0, 60) + "..."
                      : code.code}
                  </a>
                )}
              </td>
              <td>
                <span className={`badge type-${code.code_type}`}>
                  {code.code_type}
                </span>
              </td>
              <td>{code.source}</td>
              <td className="title-cell">
                {code.title && (
                  <a
                    href={code.source_url || "#"}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {code.title.length > 50
                      ? code.title.slice(0, 50) + "..."
                      : code.title}
                  </a>
                )}
              </td>
              <td>
                <span className={`badge status-${code.status}`}>
                  {code.status}
                </span>
              </td>
              <td className="date-cell">
                {code.found_at
                  ? new Date(code.found_at).toLocaleString()
                  : "-"}
              </td>
              <td className="actions-cell">
                {(code.status === "new" || code.status === "failed") && (
                  <>
                    {code.code_type === "key" && (
                      <button
                        className="btn btn-sm btn-primary"
                        onClick={() => handleRedeem(code)}
                        disabled={actionId === code.id}
                      >
                        {actionId === code.id ? "..." : "Redeem"}
                      </button>
                    )}
                    <button
                      className="btn btn-sm btn-secondary"
                      onClick={() => handleSkip(code)}
                      disabled={actionId === code.id}
                    >
                      Skip
                    </button>
                  </>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
