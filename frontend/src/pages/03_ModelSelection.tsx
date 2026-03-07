import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChevronRight, ChevronDown, ChevronUp, Check } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import Layout from '../components/Layout'
import Loader from '../components/Loader'
import { useWizard } from '../context/WizardContext'
import api from '../lib/api'

interface ModelRec {
  id: string
  name: string
  params: string
  size_gb: number
  description: string
  compatibility: 'high' | 'medium' | 'low'
  pros?: string[]
  cons?: string[]
  best_for?: string
}

const COMPAT_LABEL: Record<string, { label: string; cls: string }> = {
  high:   { label: 'Compativel',         cls: 'badge-green' },
  medium: { label: 'Parcialmente',       cls: 'badge-yellow' },
  low:    { label: 'Requer mais recursos', cls: 'badge-red' },
}

export default function ModelSelection() {
  const { state, update, setCurrentStep } = useWizard()
  const navigate = useNavigate()
  const [models, setModels] = useState<ModelRec[]>([])
  const [selected, setSelected] = useState('')
  const [expanded, setExpanded] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    setCurrentStep(3)
    const hw = state.hardware
    api.post<{ recommendations: ModelRec[] }>('/api/models/recommendations', {
      ram_gb: hw?.ram_gb ?? 8,
      vram_gb: hw?.vram_gb ?? null,
      gpu: hw?.gpu ?? null,
    })
      .then(res => { setModels(res.data.recommendations); setLoading(false) })
      .catch(() => { setError('Erro ao obter recomendacoes'); setLoading(false) })
  }, [setCurrentStep, state.hardware])

  function handleSelect(id: string) {
    setSelected(id)
    update({ selectedModel: id })
  }

  function toggleExpand(id: string) {
    setExpanded(prev => prev === id ? null : id)
  }

  return (
    <Layout title="Selecionar Modelo" subtitle="Modelos recomendados para o seu hardware">
      <div className="max-w-2xl space-y-4">

        {loading && <Loader message="Gerando recomendacoes personalizadas..." />}
        {error && <div className="card border-red-200 bg-red-50 text-red-700 text-sm">{error}</div>}

        {models.map((m, i) => {
          const compat = COMPAT_LABEL[m.compatibility] ?? COMPAT_LABEL.medium
          const isSelected = selected === m.id
          const isExpanded = expanded === m.id

          return (
            <motion.div
              key={m.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.07 }}
              onClick={() => handleSelect(m.id)}
              className={`card cursor-pointer transition-all duration-150 border-2
                ${isSelected ? 'border-accent-500 shadow-md' : 'border-surface-200 hover:border-accent-400'}`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-3 flex-1 min-w-0">
                  {/* Checkbox */}
                  <div className={`mt-0.5 flex-shrink-0 w-5 h-5 rounded-full border-2 flex items-center justify-center transition-colors
                    ${isSelected ? 'bg-accent-500 border-accent-500' : 'border-gray-300'}`}>
                    {isSelected && <Check size={12} color="white" strokeWidth={3} />}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-semibold text-gray-900">{m.name}</span>
                      <span className="text-xs text-gray-500 bg-surface-100 px-2 py-0.5 rounded-full">
                        {m.params} · {m.size_gb}GB
                      </span>
                      <span className={compat.cls}>{compat.label}</span>
                    </div>
                    <p className="text-sm text-gray-600 mt-1">{m.description}</p>
                    {m.best_for && (
                      <p className="text-xs text-accent-500 mt-1 font-medium">Ideal para: {m.best_for}</p>
                    )}
                  </div>
                </div>

                <button
                  onClick={e => { e.stopPropagation(); toggleExpand(m.id) }}
                  className="text-gray-400 hover:text-gray-600 flex-shrink-0 mt-0.5"
                >
                  {isExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                </button>
              </div>

              <AnimatePresence>
                {isExpanded && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="overflow-hidden"
                  >
                    <div className="mt-4 pt-4 border-t border-surface-200 grid grid-cols-2 gap-4 text-sm">
                      {m.pros && m.pros.length > 0 && (
                        <div>
                          <p className="font-medium text-green-700 mb-1">Pontos positivos</p>
                          <ul className="space-y-0.5">
                            {m.pros.map((p, j) => (
                              <li key={j} className="text-gray-600 flex gap-1.5">
                                <span className="text-green-500 mt-0.5">+</span> {p}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {m.cons && m.cons.length > 0 && (
                        <div>
                          <p className="font-medium text-red-700 mb-1">Limitacoes</p>
                          <ul className="space-y-0.5">
                            {m.cons.map((c, j) => (
                              <li key={j} className="text-gray-600 flex gap-1.5">
                                <span className="text-red-400 mt-0.5">−</span> {c}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          )
        })}

        {models.length > 0 && (
          <div className="flex justify-end pt-2">
            <button
              onClick={() => navigate('/topic')}
              disabled={!selected}
              className="btn-primary px-8"
            >
              Proximo: Definir Tema <ChevronRight size={16} />
            </button>
          </div>
        )}
      </div>
    </Layout>
  )
}
