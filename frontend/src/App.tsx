import { useState } from 'react'
import AppShell from './components/shell/AppShell'
import UploadStep from './components/wizard/UploadStep'
import ClassificationStep from './components/wizard/ClassificationStep'
import OpenTextStep from './components/wizard/OpenTextStep'
import ExportStep from './components/wizard/ExportStep'
import HelpModal from './components/modals/HelpModal'
import LlmConfigModal from './components/modals/LlmConfigModal'
import { api } from './api/client'
import type { StatusBadgeState } from './components/shell/Header'
import type { ProcessResult } from './api/client'

export default function App() {
  const [status,        setStatus]        = useState<StatusBadgeState>('waiting')
  const [currentStep,   setCurrentStep]   = useState<1 | 2 | 3 | 4>(1)
  const [processResult, setProcessResult] = useState<ProcessResult | null>(null)
  const [openTextIds,   setOpenTextIds]   = useState<string[]>([])
  const [helpOpen,      setHelpOpen]      = useState(false)
  const [llmConfigOpen, setLlmConfigOpen] = useState(false)

  const handleProcessed = (_qsf: File, _xlsx: File, result: ProcessResult) => {
    setProcessResult(result)
    setCurrentStep(2)
    setStatus('ready')
  }

  const handleClassificationDone = () => setCurrentStep(3)

  const handleOpenTextDone = (selectedIds: string[]) => {
    setOpenTextIds(selectedIds)
    setCurrentStep(4)
  }

  const handleBack = () => {
    if (currentStep === 2) {
      setCurrentStep(1)
      setProcessResult(null)
      setStatus('waiting')
    } else if (currentStep === 3) {
      setCurrentStep(2)
    } else if (currentStep === 4) {
      setCurrentStep(3)
    }
  }

  const handleRestart = async () => {
    await api.session.reset().catch(() => {})
    setCurrentStep(1)
    setStatus('waiting')
    setProcessResult(null)
    setOpenTextIds([])
  }

  const completedSteps: number[] =
    currentStep > 3 ? [1, 2, 3] :
    currentStep > 2 ? [1, 2] :
    currentStep > 1 ? [1] : []

  return (
    <>
      <AppShell
        currentStep={currentStep}
        completedSteps={completedSteps}
        title="Refinador"
        status={status}
        aiProvider="anthropic"
        hasContent
        onHelp={() => setHelpOpen(true)}
        onConfigureAI={() => setLlmConfigOpen(true)}
      >
        {currentStep === 1 && (
          <UploadStep onBothFiles={handleProcessed} />
        )}
        {currentStep === 2 && processResult && (
          <ClassificationStep
            result={processResult}
            onNext={handleClassificationDone}
            onBack={handleBack}
          />
        )}
        {currentStep === 3 && (
          <OpenTextStep onNext={handleOpenTextDone} onBack={handleBack} />
        )}
        {currentStep === 4 && (
          <ExportStep
            openTextIds={openTextIds}
            onBack={handleBack}
            onRestart={handleRestart}
          />
        )}
      </AppShell>

      {helpOpen && <HelpModal onClose={() => setHelpOpen(false)} />}
      {llmConfigOpen && <LlmConfigModal onClose={() => setLlmConfigOpen(false)} />}
    </>
  )
}
