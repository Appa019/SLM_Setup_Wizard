import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CheckCircle2, AlertCircle, ArrowRight, Terminal } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import Layout from '../components/Layout'
import { useWizard } from '../context/WizardContext'

interface TState {
  running: boolean; step: string; steps_done: string[]
  log: string[]; metrics: { epoch: number; loss: number | null; step: number }
  finished: boolean; error: string; model_path: string
}

export default function Training() {
  const { update, setCurrentStep } = useWizard()
  const navigate  = useNavigate()
  const [ts, setTs] = useState<TState | null>(null)
  const esRef     = useRef<EventSource | null>(null)
  const logRef    = useRef<HTMLDivElement>(null)

  useEffect(() => {
    setCurrentStep(9)
    const es = new EventSource('http://localhost:8000/api/colab/status')
    esRef.current = es
    es.onmessage = e => {
      const d: TState = JSON.parse(e.data)
      setTs(d)
      if (d.model_path) update({ modelPath: d.model_path })
      if (d.finished || d.error) es.close()
    }
    es.onerror = () => es.close()
    return () => es.close()
  }, [setCurrentStep, update])

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: 'smooth' })
  }, [ts?.log])

  return (
    <Layout title="Monitoramento do Treinamento" subtitle="Acompanhe o fine-tuning em tempo real">
      <div className="max-w-xl space-y-4">

        {/* Current step */}
        {ts?.step && (
          <div className="card flex items-center gap-3">
            {ts.finished
              ? <CheckCircle2 size={18} className="text-success-600 flex-shrink-0" />
              : (
                <motion.div
                  className="w-4 h-4 rounded-sm border-2 border-accent-500 border-t-transparent flex-shrink-0"
                  animate={{ rotate: 360 }}
                  transition={{ repeat: Infinity, duration: 0.75, ease: 'linear' }}
                />
              )
            }
            <div>
              <p className="section-title mb-0">Etapa atual</p>
              <p className="text-sm font-semibold text-gray-900 mt-0.5">{ts.step}</p>
            </div>
          </div>
        )}

        {/* Steps done */}
        {ts && ts.steps_done.length > 0 && (
          <div className="card-sm space-y-1.5">
            <p className="section-title mb-2">Etapas concluidas</p>
            {ts.steps_done.map((s, i) => (
              <div key={i} className="flex items-center gap-1.5 text-xs text-gray-600">
                <CheckCircle2 size={12} className="text-success-600 flex-shrink-0" />
                {s}
              </div>
            ))}
          </div>
        )}

        {/* Metrics */}
        {ts?.metrics && (
          <div className="grid grid-cols-3 gap-2">
            {[
              { label: 'Epoch', value: ts.metrics.epoch || '—', color: 'text-accent-500' },
              { label: 'Loss',  value: ts.metrics.loss != null ? ts.metrics.loss.toFixed(4) : '—', color: 'text-gray-900' },
              { label: 'Steps', value: ts.metrics.step || '—', color: 'text-gray-900' },
            ].map(m => (
              <div key={m.label} className="card-sm text-center py-3">
                <p className={`text-lg font-bold font-mono ${m.color}`}>{m.value}</p>
                <p className="text-[11px] text-gray-400 mt-0.5">{m.label}</p>
              </div>
            ))}
          </div>
        )}

        {/* Live log */}
        {ts && ts.log.length > 0 && (
          <div className="card-sm space-y-2">
            <div className="flex items-center gap-1.5 section-title mb-2">
              <Terminal size={11} /> Log ao vivo
            </div>
            <div ref={logRef} className="h-44 overflow-y-auto bg-gray-950 rounded p-2.5 scrollbar-thin">
              {ts.log.map((line, i) => (
                <p key={i} className="text-[11px] font-mono text-green-400 leading-5">{line}</p>
              ))}
            </div>
          </div>
        )}

        {/* Done */}
        <AnimatePresence>
          {ts?.finished && !ts.error && (
            <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
              className="flex items-center justify-between bg-success-50 border border-green-200 rounded p-4">
              <div className="flex items-center gap-2">
                <CheckCircle2 size={18} className="text-success-600" />
                <div>
                  <p className="font-semibold text-success-700 text-sm">Treinamento concluido</p>
                  {ts.model_path && <p className="text-[11px] text-success-600 font-mono">{ts.model_path}</p>}
                </div>
              </div>
              <button onClick={() => navigate('/dashboard')} className="btn-primary">
                Dashboard <ArrowRight size={14} />
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        {ts?.error && (
          <div className="flex items-start gap-2 bg-danger-50 border border-red-200 rounded p-3 text-danger-600 text-xs">
            <AlertCircle size={14} className="flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">Erro na automacao</p>
              <p className="mt-0.5">{ts.error}</p>
            </div>
          </div>
        )}

        {!ts && (
          <div className="card text-center text-gray-400 text-xs py-10">
            Aguardando inicio da automacao Colab...
          </div>
        )}

        <div className="flex justify-end">
          <button onClick={() => navigate('/dashboard')} className="btn-secondary text-xs">
            Ir para Dashboard (modelo manual)
          </button>
        </div>
      </div>
    </Layout>
  )
}
