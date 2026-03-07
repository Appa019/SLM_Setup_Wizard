import { Check } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useWizard } from '../context/WizardContext'

const STEPS = [
  { n: 1, label: 'Configuracoes',    path: '/settings' },
  { n: 2, label: 'Hardware',         path: '/hardware' },
  { n: 3, label: 'Modelo',           path: '/model' },
  { n: 4, label: 'Tema',             path: '/topic' },
  { n: 5, label: 'Config Scraping',  path: '/scraping/config' },
  { n: 6, label: 'Scraping',         path: '/scraping/progress' },
  { n: 7, label: 'Pre-processamento',path: '/preprocessing' },
  { n: 8, label: 'Colab',            path: '/colab' },
  { n: 9, label: 'Treinamento',      path: '/training' },
  { n: 10, label: 'Dashboard',       path: '/dashboard' },
]

export default function Stepper() {
  const { currentStep } = useWizard()
  const navigate = useNavigate()

  return (
    <div className="px-2 py-1">
      <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider px-2 py-2">
        Etapas
      </p>
      {STEPS.map(step => {
        const done   = step.n < currentStep
        const active = step.n === currentStep

        return (
          <button
            key={step.n}
            onClick={() => done && navigate(step.path)}
            className={`w-full flex items-center gap-2.5 px-2 py-1.5 rounded-sm text-left transition-colors duration-100
              ${active
                ? 'bg-accent-50 text-accent-600'
                : done
                  ? 'text-gray-500 hover:bg-surface-100 cursor-pointer'
                  : 'text-gray-400 cursor-default'
              }`}
          >
            {/* Step indicator */}
            <span className={`flex-shrink-0 w-5 h-5 rounded-sm flex items-center justify-center text-[10px] font-bold border
              ${active  ? 'bg-accent-500 border-accent-500 text-white' : ''}
              ${done    ? 'bg-surface-200 border-surface-200 text-gray-500' : ''}
              ${!active && !done ? 'border-surface-300 text-gray-400' : ''}
            `}>
              {done ? <Check size={10} strokeWidth={3} /> : step.n}
            </span>
            <span className={`text-xs truncate ${active ? 'font-semibold' : 'font-normal'}`}>
              {step.label}
            </span>
          </button>
        )
      })}
    </div>
  )
}
