import { Check } from 'lucide-react'
import { useWizard } from '../context/WizardContext'

const STEPS = [
  { n: 1, label: 'Configuracoes' },
  { n: 2, label: 'Hardware' },
  { n: 3, label: 'Modelo' },
  { n: 4, label: 'Tema' },
  { n: 5, label: 'Scraping Config' },
  { n: 6, label: 'Scraping' },
  { n: 7, label: 'Pre-processamento' },
  { n: 8, label: 'Colab' },
  { n: 9, label: 'Treinamento' },
  { n: 10, label: 'Dashboard' },
]

export default function Stepper() {
  const { currentStep } = useWizard()

  return (
    <nav className="flex flex-col gap-1 py-6 px-3">
      {STEPS.map(step => {
        const done = step.n < currentStep
        const active = step.n === currentStep
        return (
          <div
            key={step.n}
            className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors
              ${active ? 'bg-accent-500 text-white font-medium' : ''}
              ${done ? 'text-gray-500' : !active ? 'text-gray-400' : ''}
            `}
          >
            <span
              className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs border
                ${active ? 'bg-white text-accent-500 border-white font-bold' : ''}
                ${done ? 'bg-gray-200 border-gray-200 text-gray-500' : ''}
                ${!active && !done ? 'border-gray-300 text-gray-400' : ''}
              `}
            >
              {done ? <Check size={12} /> : step.n}
            </span>
            <span className="truncate">{step.label}</span>
          </div>
        )
      })}
    </nav>
  )
}
