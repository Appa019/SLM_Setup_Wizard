import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CheckCircle, ChevronRight, AlertCircle } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import Layout from '../components/Layout'
import { useWizard } from '../context/WizardContext'
import api from '../lib/api'

interface PreprocessState {
  running: boolean
  total_chunks: number
  done: number
  failed: number
  pairs_generated: number
  finished: boolean
  error: string
  examples: Array<{ instruction: string; input: string; output: string }>
}

export default function Preprocessing() {
  const { state, setCurrentStep } = useWizard()
  const navigate = useNavigate()
  const [ppState, setPpState] = useState<PreprocessState | null>(null)
  const [started, setStarted] = useState(false)
  const [starting, setStarting] = useState(false)
  const esRef = useRef<EventSource | null>(null)

  useEffect(() => { setCurrentStep(7) }, [setCurrentStep])

  useEffect(() => {
    return () => { esRef.current?.close() }
  }, [])

  async function handleStart() {
    setStarting(true)
    try {
      await api.post('/api/preprocessing/start', {
        topic_profile: state.topicProfile ?? {},
      })
      setStarted(true)
      startSSE()
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } }
      alert(e.response?.data?.detail ?? 'Erro ao iniciar pre-processamento')
    } finally {
      setStarting(false)
    }
  }

  function startSSE() {
    const es = new EventSource('http://localhost:8000/api/preprocessing/status')
    esRef.current = es
    es.onmessage = (event) => {
      const data: PreprocessState = JSON.parse(event.data)
      setPpState(data)
      if (data.finished || data.error) es.close()
    }
    es.onerror = () => es.close()
  }

  const pct = ppState && ppState.total_chunks > 0
    ? Math.round((ppState.done / ppState.total_chunks) * 100)
    : 0

  return (
    <Layout title="Pre-processamento" subtitle="Transformando dados brutos em pares de treinamento">
      <div className="max-w-2xl space-y-6">

        {/* Start card */}
        {!started && (
          <div className="card space-y-4">
            <div>
              <h3 className="font-semibold text-gray-900">Como funciona</h3>
              <p className="text-sm text-gray-500 mt-1">
                Os textos coletados serao enviados em lotes para o GPT-4o mini, que ira
                transforma-los em pares <span className="font-mono text-xs bg-surface-100 px-1 rounded">instruction / output</span> no
                formato JSONL — o formato padrao para fine-tuning.
              </p>
            </div>
            <div className="bg-surface-50 rounded-lg border border-surface-200 p-4 text-sm text-gray-600 space-y-1">
              {[
                'Le os textos coletados no scraping',
                'Divide em trechos de ~3.000 caracteres',
                'Envia para GPT-4o mini gerar pares instruction/output',
                'Salva em data/processed/training_data.jsonl',
              ].map((s, i) => (
                <div key={i} className="flex gap-2 items-start">
                  <span className="text-accent-500 font-bold mt-0.5">{i + 1}.</span> {s}
                </div>
              ))}
            </div>
            <div className="flex justify-end">
              <button onClick={handleStart} disabled={starting} className="btn-primary px-8">
                {starting ? 'Iniciando...' : 'Iniciar Pre-processamento'}
              </button>
            </div>
          </div>
        )}

        {/* Progress */}
        {ppState && (
          <>
            <div className="card space-y-4">
              <div className="flex justify-between text-sm">
                <span className="font-medium text-gray-700">Progresso</span>
                <span className="text-gray-500">{ppState.done} / {ppState.total_chunks} trechos</span>
              </div>
              <div className="relative h-3 bg-surface-200 rounded-full overflow-hidden">
                <motion.div
                  className="absolute inset-y-0 left-0 bg-accent-500 rounded-full"
                  animate={{ width: `${pct}%` }}
                  transition={{ duration: 0.4 }}
                />
              </div>
              <div className="grid grid-cols-3 gap-3 text-center">
                {[
                  { label: 'Processados', value: ppState.done, color: 'text-green-600' },
                  { label: 'Falhas', value: ppState.failed, color: 'text-red-500' },
                  { label: 'Pares gerados', value: ppState.pairs_generated, color: 'text-accent-500' },
                ].map(s => (
                  <div key={s.label} className="bg-surface-50 rounded-lg p-3 border border-surface-200">
                    <p className={`text-xl font-bold ${s.color}`}>{s.value}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{s.label}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Examples preview */}
            <AnimatePresence>
              {ppState.examples.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="card space-y-3"
                >
                  <p className="text-sm font-medium text-gray-700">
                    Preview — ultimos pares gerados
                  </p>
                  {ppState.examples.slice(-2).map((ex, i) => (
                    <div key={i} className="bg-surface-50 rounded-lg border border-surface-200 p-3 space-y-2 text-xs">
                      <div>
                        <span className="font-medium text-accent-500">Instrucao:</span>
                        <p className="text-gray-700 mt-0.5">{ex.instruction}</p>
                      </div>
                      <div>
                        <span className="font-medium text-gray-600">Resposta:</span>
                        <p className="text-gray-600 mt-0.5 line-clamp-3">{ex.output}</p>
                      </div>
                    </div>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>

            {/* Finished */}
            {ppState.finished && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center justify-between bg-green-50 border border-green-200 rounded-xl p-5"
              >
                <div className="flex items-center gap-3">
                  <CheckCircle size={22} className="text-green-600" />
                  <div>
                    <p className="font-semibold text-green-800">Pre-processamento concluido!</p>
                    <p className="text-sm text-green-600">
                      {ppState.pairs_generated} pares salvos em training_data.jsonl
                    </p>
                  </div>
                </div>
                <button onClick={() => navigate('/colab')} className="btn-primary">
                  Proximo: Colab <ChevronRight size={16} />
                </button>
              </motion.div>
            )}

            {ppState.error && (
              <div className="flex items-center gap-3 bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 text-sm">
                <AlertCircle size={18} />
                {ppState.error}
              </div>
            )}
          </>
        )}

      </div>
    </Layout>
  )
}
