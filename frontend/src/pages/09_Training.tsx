import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CheckCircle, Terminal, ChevronRight, AlertCircle } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import Layout from '../components/Layout'
import { useWizard } from '../context/WizardContext'

interface TrainingState {
  running: boolean
  step: string
  steps_done: string[]
  log: string[]
  metrics: { epoch: number; loss: number | null; step: number }
  finished: boolean
  error: string
  model_path: string
}

export default function Training() {
  const { update, setCurrentStep } = useWizard()
  const navigate = useNavigate()
  const [tState, setTState] = useState<TrainingState | null>(null)
  const esRef = useRef<EventSource | null>(null)
  const logRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    setCurrentStep(9)
    const es = new EventSource('http://localhost:8000/api/colab/status')
    esRef.current = es
    es.onmessage = (event) => {
      const data: TrainingState = JSON.parse(event.data)
      setTState(data)
      if (data.model_path) update({ modelPath: data.model_path })
      if (data.finished || data.error) es.close()
    }
    es.onerror = () => es.close()
    return () => es.close()
  }, [setCurrentStep, update])

  // Auto-scroll log
  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: 'smooth' })
  }, [tState?.log])

  return (
    <Layout title="Monitoramento do Treinamento" subtitle="Acompanhe o progresso do fine-tuning em tempo real">
      <div className="max-w-2xl space-y-5">

        {/* Current step */}
        {tState?.step && (
          <div className="card flex items-center gap-3">
            {tState.finished
              ? <CheckCircle size={20} className="text-green-600 flex-shrink-0" />
              : (
                <motion.div
                  className="w-5 h-5 rounded-full border-2 border-accent-500 border-t-transparent flex-shrink-0"
                  animate={{ rotate: 360 }}
                  transition={{ repeat: Infinity, duration: 0.8, ease: 'linear' }}
                />
              )
            }
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wide font-medium">Etapa atual</p>
              <p className="text-sm font-semibold text-gray-900 mt-0.5">{tState.step}</p>
            </div>
          </div>
        )}

        {/* Steps done */}
        {tState && tState.steps_done.length > 0 && (
          <div className="card space-y-2">
            <p className="text-xs font-medium text-gray-600 uppercase tracking-wide">Etapas concluidas</p>
            {tState.steps_done.map((s, i) => (
              <div key={i} className="flex items-center gap-2 text-sm text-gray-600">
                <CheckCircle size={14} className="text-green-500 flex-shrink-0" />
                {s}
              </div>
            ))}
          </div>
        )}

        {/* Metrics */}
        {tState?.metrics && (
          <div className="grid grid-cols-3 gap-3">
            {[
              { label: 'Epoch',  value: tState.metrics.epoch || '—', color: 'text-accent-500' },
              { label: 'Loss',   value: tState.metrics.loss != null ? tState.metrics.loss.toFixed(4) : '—', color: 'text-gray-900' },
              { label: 'Steps',  value: tState.metrics.step || '—', color: 'text-gray-900' },
            ].map(m => (
              <div key={m.label} className="card text-center py-4">
                <p className={`text-xl font-bold ${m.color}`}>{m.value}</p>
                <p className="text-xs text-gray-500 mt-1">{m.label}</p>
              </div>
            ))}
          </div>
        )}

        {/* Live log */}
        {tState && tState.log.length > 0 && (
          <div className="card space-y-2">
            <div className="flex items-center gap-2">
              <Terminal size={14} className="text-gray-500" />
              <p className="text-xs font-medium text-gray-600 uppercase tracking-wide">Log ao vivo</p>
            </div>
            <div
              ref={logRef}
              className="h-48 overflow-y-auto bg-gray-950 rounded-lg p-3 scrollbar-thin"
            >
              {tState.log.map((line, i) => (
                <p key={i} className="text-xs font-mono text-green-400 leading-5">{line}</p>
              ))}
            </div>
          </div>
        )}

        {/* Finished */}
        <AnimatePresence>
          {tState?.finished && !tState.error && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-center justify-between bg-green-50 border border-green-200 rounded-xl p-5"
            >
              <div className="flex items-center gap-3">
                <CheckCircle size={22} className="text-green-600" />
                <div>
                  <p className="font-semibold text-green-800">Treinamento concluido!</p>
                  {tState.model_path && (
                    <p className="text-xs text-green-600 font-mono mt-0.5">{tState.model_path}</p>
                  )}
                </div>
              </div>
              <button onClick={() => navigate('/dashboard')} className="btn-primary">
                Ver Dashboard <ChevronRight size={16} />
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        {tState?.error && (
          <div className="flex items-start gap-3 bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 text-sm">
            <AlertCircle size={18} className="flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium">Erro na automacao</p>
              <p className="text-xs mt-1">{tState.error}</p>
            </div>
          </div>
        )}

        {!tState && (
          <div className="card text-center text-gray-500 text-sm py-8">
            Aguardando inicio da automacao Colab...
          </div>
        )}

        {/* Skip to dashboard */}
        <div className="flex justify-end">
          <button onClick={() => navigate('/dashboard')} className="btn-secondary text-sm">
            Ir para Dashboard (modelo manual)
          </button>
        </div>

      </div>
    </Layout>
  )
}
