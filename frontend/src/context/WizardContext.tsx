import { createContext, useCallback, useContext, useEffect, useState } from 'react'
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
  selectedQuant: string
  selectedHfId: string
  topicProfile: Record<string, unknown> | null
  scrapingConfig: { query_count: number; sources: string[] } | null
  trainingStatus: string
  modelPath: string
  colabParams: Record<string, unknown> | null
  colabTarget: 'local' | 'colab' | ''
  colabStarted: boolean
  colabScriptPath: string
  colabNotebookPath: string
}

interface WizardContextValue {
  state: WizardState
  update: (patch: Partial<WizardState>) => void
  resetWizard: () => void
  currentStep: number
  setCurrentStep: (step: number) => void
}

const defaultState: WizardState = {
  openaiKey: '',
  googleEmail: '',
  hardware: null,
  selectedModel: '',
  selectedQuant: 'q4_k_m',
  selectedHfId: '',
  topicProfile: null,
  scrapingConfig: null,
  trainingStatus: '',
  modelPath: '',
  colabParams: null,
  colabTarget: '',
  colabStarted: false,
  colabScriptPath: '',
  colabNotebookPath: '',
}

const STORAGE_KEY = 'wizard-state'
const STEP_KEY = 'wizard-step'
const EXCLUDED_KEYS: (keyof WizardState)[] = ['openaiKey', 'googleEmail']

function loadPersistedState(): WizardState {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (raw) return { ...defaultState, ...JSON.parse(raw) }
  } catch { /* ignore */ }
  return defaultState
}

const WizardContext = createContext<WizardContextValue | null>(null)

export function WizardProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<WizardState>(loadPersistedState)
  const [currentStep, setCurrentStep] = useState(() => {
    const s = sessionStorage.getItem(STEP_KEY)
    return s ? parseInt(s, 10) : 1
  })

  useEffect(() => {
    const safe = { ...state } as Record<string, unknown>
    for (const key of EXCLUDED_KEYS) delete safe[key]
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(safe))
  }, [state])

  useEffect(() => {
    sessionStorage.setItem(STEP_KEY, String(currentStep))
  }, [currentStep])

  const update = useCallback((patch: Partial<WizardState>) =>
    setState(prev => ({ ...prev, ...patch })), [])

  const resetWizard = useCallback(() => {
    setState(defaultState)
    setCurrentStep(1)
    sessionStorage.removeItem(STORAGE_KEY)
    sessionStorage.removeItem(STEP_KEY)
  }, [])

  return (
    <WizardContext.Provider value={{ state, update, resetWizard, currentStep, setCurrentStep }}>
      {children}
    </WizardContext.Provider>
  )
}

export function useWizard() {
  const ctx = useContext(WizardContext)
  if (!ctx) throw new Error('useWizard must be inside WizardProvider')
  return ctx
}
