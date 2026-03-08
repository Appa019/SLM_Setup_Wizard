import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CheckCircle2, AlertCircle, ArrowRight, ArrowLeft, Link2 } from 'lucide-react'
import { motion } from 'framer-motion'
import Layout from '../components/Layout'
import { useWizard } from '../context/WizardContext'
import api from '../lib/api'

interface ScrapeState {
  running: boolean; total: number; done: number; failed: number
  current_url: string; bytes_collected: number
  start_time: number; finished: boolean; error: string
}

const fmtBytes = (b: number) => {
  if (b < 1024) return `${b} B`
  if (b < 1024**2) return `${(b/1024).toFixed(1)} KB`
  return `${(b/1024**2).toFixed(1)} MB`
}

const fmtEta = (done: number, total: number, t0: number) => {
  if (!done) return '...'
  const rate = done / ((Date.now()/1000) - t0)
  const rem  = (total - done) / rate
  return rem < 60 ? `${Math.ceil(rem)}s` : `${Math.ceil(rem/60)}min`
}

export default function ScrapingProgress() {
  const { setCurrentStep } = useWizard()
  const navigate = useNavigate()
  const [st, setSt] = useState<ScrapeState | null>(null)
  const [log, setLog] = useState<string[]>([])
  const esRef = useRef<EventSource | null>(null)

  useEffect(() => {
    setCurrentStep(6)
    const BASE = (api.defaults.baseURL ?? 'http://localhost:8000').replace(/\/$/, '')
    const es = new EventSource(`${BASE}/api/scraping/status`)
    esRef.current = es
    es.onmessage = e => {
      const d: ScrapeState = JSON.parse(e.data)
      setSt(d)
      if (d.current_url) setLog(prev => [d.current_url, ...prev].slice(0, 10))
      if (d.finished || d.error) es.close()
    }
    es.onerror = () => es.close()
    return () => es.close()
  }, [setCurrentStep])

  const pct = st && st.total > 0 ? Math.round((st.done / st.total) * 100) : 0

  return (
    <Layout title="Progresso do Scraping" subtitle="Coletando dados da web em tempo real">
      <div className="max-w-xl space-y-4">

        <div className="flex justify-start">
          <button onClick={() => navigate('/scraping/config')} className="btn-secondary text-xs">
            <ArrowLeft size={13} /> Voltar
          </button>
        </div>

        {/* Progress bar */}
        <div className="card space-y-3">
          <div className="flex justify-between text-xs text-gray-500">
            <span className="font-medium text-gray-700">URLs processadas</span>
            <span>{st?.done ?? 0} / {st?.total ?? 0}</span>
          </div>
          <div className="h-2 bg-surface-200 rounded-sm overflow-hidden">
            <motion.div
              className="h-full bg-accent-500"
              animate={{ width: `${pct}%` }}
              transition={{ duration: 0.4 }}
            />
          </div>
          <div className="flex justify-between items-center">
            <span className="font-bold text-accent-500 text-lg font-mono">{pct}%</span>
            {st && !st.finished && st.total > 0 && (
              <span className="text-[11px] text-gray-400">ETA: {fmtEta(st.done, st.total, st.start_time)}</span>
            )}
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-2">
          {[
            { label: 'Coletadas', value: st?.done ?? 0,                   color: 'text-success-600' },
            { label: 'Falhas',    value: st?.failed ?? 0,                  color: 'text-danger-600' },
            { label: 'Volume',    value: fmtBytes(st?.bytes_collected ?? 0), color: 'text-accent-500' },
          ].map(item => (
            <div key={item.label} className="card-sm text-center py-3">
              <p className={`text-xl font-bold font-mono ${item.color}`}>{item.value}</p>
              <p className="text-[11px] text-gray-400 mt-0.5">{item.label}</p>
            </div>
          ))}
        </div>

        {/* Live URL log */}
        {log.length > 0 && (
          <div className="card-sm space-y-1.5">
            <div className="flex items-center gap-1.5 section-title mb-2">
              <Link2 size={11} /> URLs recentes
            </div>
            {log.map((url, i) => (
              <p key={i} className={`text-[11px] font-mono truncate ${i === 0 ? 'text-gray-700' : 'text-gray-400'}`}>
                {url}
              </p>
            ))}
          </div>
        )}

        {/* Active indicator */}
        {st?.running && st.current_url && (
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <motion.div
              className="w-1.5 h-1.5 bg-green-500 rounded-sm flex-shrink-0"
              animate={{ opacity: [1, 0.3, 1] }}
              transition={{ repeat: Infinity, duration: 1.2 }}
            />
            Processando: <span className="font-mono text-gray-700 truncate">{st.current_url}</span>
          </div>
        )}

        {/* Done */}
        {st?.finished && (
          <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
            className="flex items-center justify-between bg-success-50 border border-green-200 rounded p-4">
            <div className="flex items-center gap-2">
              <CheckCircle2 size={18} className="text-success-600" />
              <div>
                <p className="font-semibold text-success-700 text-sm">Scraping concluido</p>
                <p className="text-xs text-success-600">{st.done} paginas · {fmtBytes(st.bytes_collected)}</p>
              </div>
            </div>
            <button onClick={() => navigate('/preprocessing')} className="btn-primary">
              Pre-processar <ArrowRight size={14} />
            </button>
          </motion.div>
        )}

        {st?.error && (
          <div className="flex items-center gap-2 bg-danger-50 border border-red-200 rounded p-3 text-danger-600 text-xs">
            <AlertCircle size={15} /> {st.error}
          </div>
        )}

        {!st && (
          <div className="card text-center text-gray-400 text-sm py-10">
            Aguardando conexao SSE...
          </div>
        )}
      </div>
    </Layout>
  )
}
