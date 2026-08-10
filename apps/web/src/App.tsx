import { SiteHeader } from './components/SiteHeader'
import { useVerificationWorkflow } from './hooks/useVerificationWorkflow'
import { VerificationPage } from './pages/VerificationPage'

export function App() {
  const workflow = useVerificationWorkflow()

  return (
    <div className="app-shell">
      <SiteHeader readiness={workflow.readiness} onRetry={workflow.checkReadiness} />

      <div className="demo-banner" role="note">
        <strong>Public COLA metadata · local review only</strong>
        <span>Registry data is read-only. No government system is updated.</span>
      </div>

      <VerificationPage workflow={workflow} />

      <footer><span>Distilled spirits label verification</span></footer>
    </div>
  )
}
