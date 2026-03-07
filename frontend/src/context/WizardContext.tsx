import { createContext, useContext, useState } from 'react'
import type { ReactNode } from 'react'

export interface HardwareInfo {
  cpu: string
  ram_gb: number
  gpu?: string
  vram_gb?: number
  disk_free_gb: number
  os: string
}

export interface WizardState {
  openaiKey: string
  googleEmail: string
  hardware: HardwareInfo | null
  selectedModel: string
  topicProfile: Record<string, unknown> | null
  scrapingConfig: { url_count: number; sources: string[] } | null
  trainingStatus: string
  modelPath: string
}

interface WizardContextValue {
  state: WizardState
  update: (patch: Partial<WizardState>) => void
  currentStep: number
  setCurrentStep: (step: number) => void
}

const defaultState: WizardState = {
  openaiKey: '',
  googleEmail: '',
  hardware: null,
  selectedModel: '',
  topicProfile: null,
  scrapingConfig: null,
  trainingStatus: '',
  modelPath: '',
}

const WizardContext = createContext<WizardContextValue | null>(null)

export function WizardProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<WizardState>(defaultState)
  const [currentStep, setCurrentStep] = useState(1)

  const update = (patch: Partial<WizardState>) =>
    setState(prev => ({ ...prev, ...patch }))

  return (
    <WizardContext.Provider value={{ state, update, currentStep, setCurrentStep }}>
      {children}
    </WizardContext.Provider>
  )
}

export function useWizard() {
  const ctx = useContext(WizardContext)
  if (!ctx) throw new Error('useWizard must be inside WizardProvider')
  return ctx
}
