import { lazy, Suspense } from "react"
import "./App.css"

const Dashboard = lazy(() => import("./components/Dashboard").then(m => ({ default: m.Dashboard })))

function App() {
  return (
    <Suspense fallback={<div className="loading">Loading...</div>}>
      <Dashboard />
    </Suspense>
  )
}

export default App
