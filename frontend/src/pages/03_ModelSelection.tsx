import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Check, ArrowRight, ExternalLink } from 'lucide-react'
import { motion } from 'framer-motion'
import Layout from '../components/Layout'
import Loader from '../components/Loader'
import { useWizard } from '../context/WizardContext'
import api from '../lib/api'

interface QuantOption {
  type:          string
  label:         string
  vram_gb:       number
  compatibility: 'high' | 'medium' | 'low'
}

interface ModelRec {
  id:             string
  name:           string
  params:         string
  family:         string
  hf_id:          string
  description:    string
  context_window: number
  license:        string
  compatibility:  'high' | 'medium' | 'low'
  selected_quant: string
  quant_options:  QuantOption[]
  pros?:          string[]
  cons?:          string[]
  best_for?:      string
}

const COMPAT: Record<string, { label: string; cls: string }> = {
  high:   { label: 'Compativel',   cls: 'badge-green'  },
  medium: { label: 'Parcialmente', cls: 'badge-yellow' },
  low:    { label: 'Insuficiente', cls: 'badge-red'    },
}

function fmtCtx(n: number): string {
  if (n >= 1000000) return `${(n / 1000000).toFixed(0)}M ctx`
  if (n >= 1000)    return `${(n / 1000).toFixed(0)}k ctx`
  return `${n} ctx`
}

export default function ModelSelection() {
  const { state, update, setCurrentStep } = useWizard()
  const navigate = useNavigate()

  const [models, setModels]               = useState<ModelRec[]>([])
  const [selected, setSelected]           = useState('')
  const [selectedQuant, setSelectedQuant] = useState<Record<string, string>>({})
  const [loading, setLoading]             = useState(true)
  const [error, setError]                 = useState('')

  useEffect(() => {
    setCurrentStep(3)
    const hw = state.hardware
    api.post<{ recommendations: ModelRec[] }>('/api/models/recommendations', {
      ram_gb:  hw?.ram_gb  ?? 8,
      vram_gb: hw?.vram_gb ?? null,
      gpu:     hw?.gpu     ?? null,
    })
      .then(res => {
        const recs = res.data.recommendations
        setModels(recs)
        const defaults: Record<string, string> = {}
        recs.forEach(m => { defaults[m.id] = m.selected_quant })
        setSelectedQuant(defaults)
        setLoading(false)
      })
      .catch(() => { setError('Erro ao obter recomendacoes'); setLoading(false) })
  }, [setCurrentStep, state.hardware])

  function selectModel(m: ModelRec) {
    setSelected(m.id)
    update({
      selectedModel: m.id,
      selectedHfId:  m.hf_id,
      selectedQuant: selectedQuant[m.id] ?? m.selected_quant,
    })
  }

  function selectVariant(modelId: string, quantType: string) {
    setSelectedQuant(prev => ({ ...prev, [modelId]: quantType }))
    if (selected === modelId) {
      update({ selectedQuant: quantType })
    }
  }

  return (
    <Layout title="Selecionar Modelo" subtitle="Modelos escolhidos pelo GPT-5.4 para o seu hardware">
      <div className="max-w-xl space-y-3">
        {loading && <Loader message="GPT-5.4 analisando seu hardware..." />}
        {error   && <div className="card border-red-200 bg-danger-50 text-danger-600 text-xs p-3">{error}</div>}

        {models.map((m, i) => {
          const compat     = COMPAT[m.compatibility] ?? COMPAT.medium
          const isSelected = selected === m.id

          return (
            <motion.div
              key={m.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.07 }}
              onClick={() => selectModel(m)}
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

                <div className="flex-1 min-w-0 space-y-3">

                  {/* Header */}
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-semibold text-gray-900 text-sm">{m.name}</span>
                      <span className="code">{m.params}</span>
                      {m.family && <span className="code">{m.family}</span>}
                      <span className={compat.cls}>{compat.label}</span>
                      {i === 0 && (
                        <span className="badge-green text-[10px]">Recomendado IA</span>
                      )}
                    </div>

                    {/* Meta row */}
                    <div className="flex items-center gap-3 mt-1.5 flex-wrap text-[11px] text-gray-400">
                      {m.context_window > 0 && (
                        <span>{fmtCtx(m.context_window)}</span>
                      )}
                      {m.license && <span>· {m.license}</span>}
                      {m.hf_id && (
                        <a
                          href={`https://huggingface.co/${m.hf_id}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={e => e.stopPropagation()}
                          className="flex items-center gap-0.5 text-accent-500 hover:text-accent-600"
                        >
                          <ExternalLink size={10} />
                          {m.hf_id}
                        </a>
                      )}
                    </div>

                    <p className="text-xs text-gray-500 mt-1.5 leading-relaxed">{m.description}</p>
                    {m.best_for && (
                      <p className="text-[11px] text-accent-500 mt-1 font-medium">
                        Ideal para: {m.best_for}
                      </p>
                    )}
                  </div>

                  {/* Pros / Cons */}
                  {((m.pros && m.pros.length > 0) || (m.cons && m.cons.length > 0)) && (
                    <div className="grid grid-cols-2 gap-2 text-[11px]">
                      {m.pros && m.pros.length > 0 && (
                        <div className="space-y-0.5">
                          <p className="font-semibold text-success-600 mb-1">Pontos positivos</p>
                          {m.pros.map((p, j) => (
                            <p key={j} className="text-gray-600 flex gap-1">
                              <span className="text-success-600 flex-shrink-0">+</span>{p}
                            </p>
                          ))}
                        </div>
                      )}
                      {m.cons && m.cons.length > 0 && (
                        <div className="space-y-0.5">
                          <p className="font-semibold text-danger-600 mb-1">Limitacoes</p>
                          {m.cons.map((c, j) => (
                            <p key={j} className="text-gray-600 flex gap-1">
                              <span className="text-danger-600 flex-shrink-0">-</span>{c}
                            </p>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Quant variants */}
                  <div onClick={e => e.stopPropagation()}>
                    <p className="section-title mb-2">Variantes disponíveis</p>
                    <div className="space-y-1">
                      {m.quant_options.map(opt => {
                        const isVariantSelected = selectedQuant[m.id] === opt.type
                        const qCompat = COMPAT[opt.compatibility] ?? COMPAT.medium
                        return (
                          <label
                            key={opt.type}
                            onClick={e => { e.stopPropagation(); selectVariant(m.id, opt.type) }}
                            className={`flex items-center gap-2 p-2 rounded border cursor-pointer transition-colors text-xs
                              ${isVariantSelected
                                ? 'border-accent-400 bg-accent-50'
                                : 'border-surface-200 hover:border-surface-300 bg-white'}`}
                          >
                            <input
                              type="radio"
                              name={`quant-${m.id}`}
                              value={opt.type}
                              checked={isVariantSelected}
                              onChange={() => selectVariant(m.id, opt.type)}
                              className="accent-accent-500"
                            />
                            <span className="font-mono font-medium text-gray-800 w-32 flex-shrink-0">{opt.label}</span>
                            <span className="text-gray-500">{opt.vram_gb} GB VRAM</span>
                            <span className={`ml-auto ${qCompat.cls}`}>
                              {opt.compatibility === 'high' ? 'OK' : opt.compatibility === 'medium' ? 'Limite' : 'Insuf.'}
                            </span>
                          </label>
                        )
                      })}
                    </div>
                  </div>

                </div>
              </div>
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
