import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChevronDown, ChevronUp, Check, ArrowRight } from 'lucide-react'
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

const COMPAT: Record<string, { label: string; cls: string }> = {
  high:   { label: 'Compativel',   cls: 'badge-green'  },
  medium: { label: 'Parcialmente', cls: 'badge-yellow' },
  low:    { label: 'Insuficiente', cls: 'badge-red'    },
}

export default function ModelSelection() {
  const { state, update, setCurrentStep } = useWizard()
  const navigate  = useNavigate()
  const [models, setModels]     = useState<ModelRec[]>([])
  const [selected, setSelected] = useState('')
  const [expanded, setExpanded] = useState<string | null>(null)
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState('')

  useEffect(() => {
    setCurrentStep(3)
    const hw = state.hardware
    api.post<{ recommendations: ModelRec[] }>('/api/models/recommendations', {
      ram_gb:  hw?.ram_gb  ?? 8,
      vram_gb: hw?.vram_gb ?? null,
      gpu:     hw?.gpu     ?? null,
    })
      .then(res => { setModels(res.data.recommendations); setLoading(false) })
      .catch(() => { setError('Erro ao obter recomendacoes'); setLoading(false) })
  }, [setCurrentStep, state.hardware])

  function select(id: string) { setSelected(id); update({ selectedModel: id }) }

  return (
    <Layout title="Selecionar Modelo" subtitle="Modelos recomendados para o seu hardware">
      <div className="max-w-xl space-y-3">
        {loading && <Loader message="Consultando recomendacoes..." />}
        {error && <div className="card border-red-200 bg-danger-50 text-danger-600 text-xs p-3">{error}</div>}

        {models.map((m, i) => {
          const compat     = COMPAT[m.compatibility] ?? COMPAT.medium
          const isSelected = selected === m.id
          const isExpanded = expanded === m.id

          return (
            <motion.div
              key={m.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.06 }}
              onClick={() => select(m.id)}
              className={`card cursor-pointer transition-colors duration-100 border-2
                ${isSelected
                  ? 'border-accent-500 bg-accent-50'
                  : 'border-surface-200 hover:border-surface-300'}`}
            >
              <div className="flex items-start gap-3">
                {/* Checkbox */}
                <div className={`mt-0.5 w-4 h-4 rounded-sm border-2 flex items-center justify-center flex-shrink-0 transition-colors
                  ${isSelected ? 'bg-accent-500 border-accent-500' : 'border-gray-300'}`}>
                  {isSelected && <Check size={10} color="white" strokeWidth={3} />}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-semibold text-gray-900 text-sm">{m.name}</span>
                    <span className="code">{m.params} · {m.size_gb}GB</span>
                    <span className={compat.cls}>{compat.label}</span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1 leading-relaxed">{m.description}</p>
                  {m.best_for && (
                    <p className="text-[11px] text-accent-500 mt-1 font-medium">
                      Ideal para: {m.best_for}
                    </p>
                  )}
                </div>

                <button
                  onClick={e => { e.stopPropagation(); setExpanded(prev => prev === m.id ? null : m.id) }}
                  className="text-gray-400 hover:text-gray-600 flex-shrink-0"
                >
                  {isExpanded ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
                </button>
              </div>

              <AnimatePresence>
                {isExpanded && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="overflow-hidden"
                  >
                    <div className="mt-3 pt-3 border-t border-surface-200 grid grid-cols-2 gap-3 text-xs">
                      {m.pros && m.pros.length > 0 && (
                        <div>
                          <p className="font-semibold text-success-600 mb-1">Pontos positivos</p>
                          {m.pros.map((p, j) => (
                            <p key={j} className="text-gray-600 flex gap-1 mb-0.5">
                              <span className="text-success-600">+</span>{p}
                            </p>
                          ))}
                        </div>
                      )}
                      {m.cons && m.cons.length > 0 && (
                        <div>
                          <p className="font-semibold text-danger-600 mb-1">Limitacoes</p>
                          {m.cons.map((c, j) => (
                            <p key={j} className="text-gray-600 flex gap-1 mb-0.5">
                              <span className="text-danger-600">−</span>{c}
                            </p>
                          ))}
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
          <div className="flex justify-end pt-1">
            <button onClick={() => navigate('/topic')} disabled={!selected} className="btn-primary">
              Definir Tema <ArrowRight size={14} />
            </button>
          </div>
        )}
      </div>
    </Layout>
  )
}
