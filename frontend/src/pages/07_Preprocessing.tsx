import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CheckCircle2, AlertCircle, ArrowRight, ArrowLeft, Sparkles, Clock } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import Layout from '../components/Layout'
import { useWizard } from '../context/WizardContext'
import api from '../lib/api'

interface PPState {
  running: boolean; total_chunks: number; done: number; failed: number
  pairs_generated: number; finished: boolean; error: string
  examples: Array<{ instruction: string; input: string; output: string }>
}

export default function Preprocessing() {
  const { state, setCurrentStep } = useWizard()
  const navigate = useNavigate()
  const [ppState, setPPState] = useState<PPState | null>(null)
  const [started, setStarted] = useState(false)
  const [starting, setStarting] = useState(false)
  const [scrapingDone, setScrapingDone] = useState<boolean | null>(null)
  const esRef = useRef<EventSource | null>(null)

  useEffect(() => {
    api.get('/api/scraping/state').then(r => setScrapingDone(r.data.finished ?? false)).catch(() => setScrapingDone(false))
  }, [])

  useEffect(() => { setCurrentStep(7) }, [setCurrentStep])
  useEffect(() => () => esRef.current?.close(), [])

  async function start() {
    setStarting(true)
    try {
      await api.post('/api/preprocessing/start', { topic_profile: state.topicProfile ?? {} })
      setStarted(true)
      const BASE = (api.defaults.baseURL ?? 'http://localhost:8000').replace(/\/$/, '')
      const es = new EventSource(`${BASE}/api/preprocessing/status`)
      esRef.current = es
      es.onmessage = e => {
        const d: PPState = JSON.parse(e.data)
        setPPState(d)
        if (d.finished || d.error) es.close()
      }
      es.onerror = () => es.close()
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } }
      alert(e.response?.data?.detail ?? 'Erro ao iniciar')
    } finally { setStarting(false) }
  }

  const pct = ppState && ppState.total_chunks > 0
    ? Math.round((ppState.done / ppState.total_chunks) * 100)
    : 0

  return (
    <Layout title="Pre-processamento" subtitle="Transformando textos em pares de treinamento">
      <div className="max-w-xl space-y-4">

        {/* Not started */}
        {!started && (
          <div className="card space-y-4">
            {scrapingDone === false && (
              <div className="flex items-center gap-2 bg-amber-50 border border-amber-200 rounded p-3 text-amber-700 text-xs">
                <Clock size={14} className="flex-shrink-0" />
                <span>Finalize o scraping antes de iniciar o pre-processamento. Volte para a etapa anterior.</span>
              </div>
            )}
            <h3 className="text-sm font-semibold text-gray-900 border-b border-surface-200 pb-2">
              Como funciona
            </h3>
            <div className="space-y-2">
              {[
                'Le os textos coletados no scraping',
                'Divide em trechos de ~3.000 caracteres',
                'Envia para GPT-4o mini gerar pares instruction / output',
                'Salva em data/processed/training_data.jsonl',
              ].map((s, i) => (
                <div key={i} className="flex gap-2 text-xs text-gray-600">
                  <span className="w-4 h-4 rounded-sm bg-accent-500 text-white flex items-center justify-center text-[10px] font-bold flex-shrink-0">
                    {i + 1}
                  </span>
                  {s}
                </div>
              ))}
            </div>
            <div className="flex justify-between items-center border-t border-surface-200 pt-3">
              <button onClick={() => navigate('/scraping/progress')} className="btn-secondary">
                <ArrowLeft size={14} /> Voltar
              </button>
              <button onClick={start} disabled={starting || scrapingDone === false} className="btn-primary disabled:opacity-40 disabled:cursor-not-allowed">
                {starting ? 'Iniciando...' : 'Iniciar Pre-processamento'}
              </button>
            </div>
          </div>
        )}

        {/* Progress */}
        {ppState && (
          <>
            <div className="card space-y-3">
              <div className="flex justify-between text-xs text-gray-500">
                <span className="font-medium text-gray-700">Trechos processados</span>
                <span>{ppState.done} / {ppState.total_chunks}</span>
              </div>
              <div className="h-2 bg-surface-200 rounded-sm overflow-hidden">
                <motion.div className="h-full bg-accent-500" animate={{ width: `${pct}%` }} transition={{ duration: 0.4 }} />
              </div>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { label: 'Processados',   value: ppState.done,            color: 'text-success-600' },
                  { label: 'Falhas',        value: ppState.failed,          color: 'text-danger-600' },
                  { label: 'Pares gerados', value: ppState.pairs_generated, color: 'text-accent-500' },
                ].map(s => (
                  <div key={s.label} className="bg-surface-50 border border-surface-200 rounded p-2 text-center">
                    <p className={`text-lg font-bold font-mono ${s.color}`}>{s.value}</p>
                    <p className="text-[10px] text-gray-400 mt-0.5">{s.label}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Preview */}
            <AnimatePresence>
              {ppState.examples.length > 0 && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="card space-y-2">
                  <div className="flex items-center gap-1.5 section-title mb-1">
                    <Sparkles size={11} /> Preview — ultimos pares
                  </div>
                  {ppState.examples.slice(-2).map((ex, i) => (
                    <div key={i} className="terminal-box space-y-1.5">
                      <div>
                        <span className="text-teal-400 font-bold">INST: </span>
                        <span className="text-green-300">{ex.instruction}</span>
                      </div>
                      <div>
                        <span className="text-gray-500 font-bold">OUT:  </span>
                        <span className="text-green-500/70 line-clamp-2">{ex.output}</span>
                      </div>
                    </div>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>

            {/* Done */}
            {ppState.finished && !ppState.error && (
              <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
                className="flex items-center justify-between bg-success-50 border border-green-200 rounded p-4">
                <div className="flex items-center gap-2">
                  <CheckCircle2 size={18} className="text-success-600" />
                  <div>
                    <p className="font-semibold text-success-700 text-sm">Pre-processamento concluido</p>
                    <p className="text-xs text-success-600">{ppState.pairs_generated} pares em training_data.jsonl</p>
                  </div>
                </div>
                <button onClick={() => navigate('/colab')} className="btn-primary">
                  Colab <ArrowRight size={14} />
                </button>
              </motion.div>
            )}
            {ppState.error && (
              <div className="flex items-center gap-2 bg-danger-50 border border-red-200 rounded p-3 text-danger-600 text-xs">
                <AlertCircle size={15} /> {ppState.error}
              </div>
            )}
          </>
        )}
      </div>
    </Layout>
  )
}
