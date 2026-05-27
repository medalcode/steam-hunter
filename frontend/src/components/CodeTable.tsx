import { useEffect, useState, useCallback } from "react"
import type { FoundCode } from "../types"
import {
  fetchCodes,
  redeemCode,
  skipCode,
  validateCode,
  autoEnterGiveaway,
} from "../api/client"

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

  const showMsg = (text: string) => {
    setMessage(text)
    setTimeout(() => setMessage(null), 5000)
  }

  const handleRedeem = async (code: FoundCode) => {
    setActionId(code.id)
    const result = await redeemCode(code.id)
    showMsg(
      result.success ? `\u2705 Redeemed: ${code.code}` : `\u274c Failed: ${result.message || "Unknown"}`,
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

  const handleValidate = async (code: FoundCode) => {
    setActionId(code.id)
    const result = await validateCode(code.id)
    showMsg(result.valid ? `\u2705 Valid: ${result.reason}` : `\u26a0 Invalid: ${result.reason}`)
    setActionId(null)
    load()
  }

  const handleAutoEnter = async (code: FoundCode) => {
    setActionId(code.id)
    const result = await autoEnterGiveaway(code.code, code.title || "")
    showMsg(result.success ? `\u2728 ${result.message}` : `\u274c ${result.message}`)
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
      <div className="table-wrapper">
        <table className="code-table">
          <thead>
            <tr>
              <th>Code / Link</th>
              <th>Type</th>
              <th>Source</th>
              <th>Title</th>
              <th>Status</th>
              <th>Validation</th>
              <th>Found</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {codes.length === 0 && (
              <tr>
                <td colSpan={8} className="empty">
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
                    <a href={code.code} target="_blank" rel="noopener noreferrer">
                      {code.code.length > 60 ? code.code.slice(0, 60) + "..." : code.code}
                    </a>
                  )}
                </td>
                <td>
                  <span className={`badge type-${code.code_type}`}>{code.code_type}</span>
                </td>
                <td className="source-cell">{code.source}</td>
                <td className="title-cell">
                  {code.title && (
                    <a href={code.source_url || "#"} target="_blank" rel="noopener noreferrer">
                      {code.title.length > 50 ? code.title.slice(0, 50) + "..." : code.title}
                    </a>
                  )}
                </td>
                <td>
                  <span className={`badge status-${code.status}`}>{code.status}</span>
                </td>
                <td className="validation-cell">
                  {code.validation_status ? (
                    <span className={`badge val-${code.validation_status}`}>
                      {code.validation_status}
                    </span>
                  ) : (
                    <span className="badge val-pending">pending</span>
                  )}
                  {code.validation_reason && (
                    <div className="val-reason">{code.validation_reason}</div>
                  )}
                </td>
                <td className="date-cell">
                  {code.found_at ? new Date(code.found_at).toLocaleString() : "-"}
                </td>
                <td className="actions-cell">
                  {(code.status === "new" || code.status === "failed") && (
                    <>
                      {code.code_type === "key" && (
                        <>
                          <button
                            className="btn btn-xs btn-primary"
                            onClick={() => handleRedeem(code)}
                            disabled={actionId === code.id}
                          >
                            {actionId === code.id ? "..." : "Redeem"}
                          </button>
                          <button
                            className="btn btn-xs btn-outline"
                            onClick={() => handleValidate(code)}
                            disabled={actionId === code.id}
                          >
                            Validate
                          </button>
                        </>
                      )}
                      {code.code_type === "giveaway" && (
                        <button
                          className="btn btn-xs btn-primary"
                          onClick={() => handleAutoEnter(code)}
                          disabled={actionId === code.id}
                        >
                          {actionId === code.id ? "..." : "Auto-Enter"}
                        </button>
                      )}
                      <button
                        className="btn btn-xs btn-outline"
                        onClick={() => handleSkip(code)}
                        disabled={actionId === code.id}
                      >
                        Skip
                      </button>
                    </>
                  )}
                  {code.status === "redeemed" && code.steam_account_id && (
                    <span className="acct-badge">acct #{code.steam_account_id}</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
