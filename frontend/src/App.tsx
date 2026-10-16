import { useEffect, useState } from 'react'

type Health = { status: string; falkordb?: string; graph_module_ver?: number; error?: string }

// M1 placeholder: proves the frontend can reach the backend. The real UI lands in M8.
export default function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/health')
      .then((r) => r.json())
      .then(setHealth)
      .catch((e) => setError(String(e)))
  }, [])

  return (
    <main className="placeholder">
      <h1>DOMINO</h1>
      <p>Multi-tier supply-chain recovery agent on FalkorDB.</p>
      <pre>{error ?? (health ? JSON.stringify(health, null, 2) : 'checking backend…')}</pre>
    </main>
  )
}
