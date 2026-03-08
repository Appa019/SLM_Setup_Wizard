import { useNavigate } from 'react-router-dom'
import { useWizard } from '../context/WizardContext'

const STEPS = [
  { n: 1, label: 'Configuracoes',    path: '/settings',           icon: '/01_icone.png' },
  { n: 2, label: 'Hardware',         path: '/hardware',           icon: '/02_icone.png' },
  { n: 3, label: 'Modelo',           path: '/model',              icon: '/03_icone.png' },
  { n: 4, label: 'Tema',             path: '/topic',              icon: '/04_icone.png' },
  { n: 5, label: 'Config Scraping',  path: '/scraping/config',    icon: '/05_icone.png' },
  { n: 6, label: 'Scraping',         path: '/scraping/progress',  icon: '/06_icone.png' },
  { n: 7, label: 'Pre-processamento',path: '/preprocessing',      icon: '/07_icone.png' },
  { n: 8, label: 'Colab',            path: '/colab',              icon: '/08_icone.png' },
  { n: 9, label: 'Treinamento',      path: '/training',           icon: '/09_icone.png' },
  { n: 10, label: 'Dashboard',       path: '/dashboard',          icon: '/10_icone.png' },
]

export default function Stepper() {
  const { currentStep } = useWizard()
  const navigate = useNavigate()

  return (
    <div className="px-2 py-1">
      {STEPS.map(step => {
        const done   = step.n < currentStep
        const active = step.n === currentStep

        return (
          <button
            key={step.n}
            onClick={() => navigate(step.path)}
            className={`w-full flex items-center gap-2.5 px-2 py-1.5 text-left transition-colors duration-100 cursor-pointer
              ${active
                ? 'bg-accent-50 border-l-2 border-l-accent-500 text-accent-700'
                : done
                  ? 'text-gray-500 hover:bg-surface-100 border-l-2 border-l-transparent'
                  : 'text-gray-400 hover:bg-surface-100 border-l-2 border-l-transparent'
              }`}
          >
            <img
              src={step.icon}
              className={`w-5 h-5 flex-shrink-0
                ${active ? 'opacity-100' : done ? 'opacity-50' : 'opacity-25 grayscale'}`}
              alt=""
            />
            <span className={`font-display text-[11px] tracking-wide truncate ${active ? 'font-bold' : 'font-normal'}`}>
              {step.label}
            </span>
          </button>
        )
      })}
    </div>
  )
}
