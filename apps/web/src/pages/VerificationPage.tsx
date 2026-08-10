import { DecisionDialog } from '../components/DecisionDialog'
import { VerificationIntake } from '../components/VerificationIntake'
import { VerificationWorkspace } from '../components/VerificationWorkspace'
import type { VerificationWorkflow } from '../hooks/useVerificationWorkflow'

interface VerificationPageProps {
  workflow: VerificationWorkflow
}

export function VerificationPage({ workflow }: VerificationPageProps) {
  return (
    <>
      <main id="main-content">
        <section className="hero" aria-labelledby="page-heading">
          <div>
            <p className="eyebrow">Distilled spirits</p>
            <h1 id="page-heading">Verify a product label</h1>
          </div>
          <p>
            Add one or more photos. Label Lens identifies the application and checks the label
            against its approved record.
          </p>
        </section>

        <div className="workflow-layout">
          <VerificationIntake workflow={workflow} />
          <VerificationWorkspace workflow={workflow} />
        </div>
      </main>

      {workflow.decisionAction && workflow.verification ? (
        <DecisionDialog
          action={workflow.decisionAction}
          verification={workflow.verification}
          busy={workflow.decisionBusy}
          error={workflow.decisionError}
          onClose={workflow.closeDecision}
          onSubmit={(decision) => void workflow.handleDecision(decision)}
        />
      ) : null}
    </>
  )
}
