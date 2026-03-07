import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CheckCircle, AlertCircle, ChevronRight } from 'lucide-react'
import { motion } from 'framer-motion'
import Layout from '../components/Layout'
import { useWizard } from '../context/WizardContext'

interface ScrapingState {
  running: boolean
  total: number
  done: number
  failed: number
  current_url: string
  bytes_collected: number
  start_time: number
  finished: boolean
  error: string
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatEta(done: number, total: number, startTime: number): string {
  if (done === 0) return 'calculando...'
  const elapsed = (Date.now() / 1000) - startTime
  const rate = done / elapsed
  const remaining = (total - done) / rate
  if (remaining < 60) return `~${Math.ceil(remaining)}s`
  return `~${Math.ceil(remaining / 60)}min`
}

export default function ScrapingProgress() {
  const { setCurrentStep } = useWizard()
  const navigate = useNavigate()
  const [state, setState] = useState<ScrapingState | null>(null)
  const [recentUrls, setRecentUrls] = useState<string[]>([])
  const esRef = useRef<EventSource | null>(null)

  useEffect(() => {
    setCurrentStep(6)
    const es = new EventSource('http://localhost:8000/api/scraping/status')
    esRef.current = es

    es.onmessage = (event) => {
      const data: ScrapingState = JSON.parse(event.data)
      setState(data)
      if (data.current_url) {
        setRecentUrls(prev => {
          const next = [data.current_url, ...prev.filter(u => u !== data.current_url)]
          return next.slice(0, 8)
        })
      }
    }

    es.onerror = () => { es.close() }

    return () => { es.close() }
  }, [setCurrentStep])

  const pct = state && state.total > 0
    ? Math.round((state.done / state.total) * 100)
    : 0

  return (
    <Layout title="Progresso do Scraping" subtitle="Coletando dados da web em tempo real">
      <div className="max-w-2xl space-y-5">

        {/* Main progress */}
        <div className="card space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700">Progresso geral</span>
            <span className="text-sm text-gray-500">
              {state?.done ?? 0} / {state?.total ?? 0} URLs
            </span>
          </div>

          {/* Progress bar */}
          <div className="relative h-3 bg-surface-200 rounded-full overflow-hidden">
            <motion.div
              className="absolute inset-y-0 left-0 bg-accent-500 rounded-full"
              animate={{ width: `${pct}%` }}
              transition={{ duration: 0.5 }}
            />
          </div>

          <div className="flex items-center justify-between text-sm">
            <span className="font-semibold text-accent-500 text-lg">{pct}%</span>
            {state && !state.finished && state.total > 0 && (
              <span className="text-gray-500 text-xs">
                ETA: {formatEta(state.done, state.total, state.start_time)}
              </span>
            )}
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: 'Coletadas', value: state?.done ?? 0, color: 'text-green-600' },
            { label: 'Falhas', value: state?.failed ?? 0, color: 'text-red-500' },
            { label: 'Volume', value: formatBytes(state?.bytes_collected ?? 0), color: 'text-accent-500' },
          ].map(item => (
            <div key={item.label} className="card text-center py-4">
              <p className={`text-2xl font-bold ${item.color}`}>{item.value}</p>
              <p className="text-xs text-gray-500 mt-1">{item.label}</p>
            </div>
          ))}
        </div>

        {/* Current URL */}
        {state?.current_url && !state.finished && (
          <div className="card space-y-3">
            <div className="flex items-center gap-2">
              <motion.div
                className="w-2 h-2 bg-green-500 rounded-full"
                animate={{ opacity: [1, 0.3, 1] }}
                transition={{ repeat: Infinity, duration: 1.2 }}
              />
              <span className="text-xs font-medium text-gray-600 uppercase tracking-wide">
                Processando agora
              </span>
            </div>
            <p className="text-xs font-mono text-gray-500 truncate">{state.current_url}</p>
          </div>
        )}

        {/* Recent URLs log */}
        {recentUrls.length > 0 && (
          <div className="card space-y-2">
            <p className="text-xs font-medium text-gray-600 uppercase tracking-wide">
              URLs recentes
            </p>
            <div className="space-y-1">
              {recentUrls.map((url, i) => (
                <p key={i} className="text-xs font-mono text-gray-400 truncate">{url}</p>
              ))}
            </div>
          </div>
        )}

        {/* Finished */}
        {state?.finished && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center justify-between bg-green-50 border border-green-200 rounded-xl p-5"
          >
            <div className="flex items-center gap-3">
              <CheckCircle size={22} className="text-green-600" />
              <div>
                <p className="font-semibold text-green-800">Scraping concluido!</p>
                <p className="text-sm text-green-600">
                  {state.done} paginas · {formatBytes(state.bytes_collected)} coletados
                </p>
              </div>
            </div>
            <button onClick={() => navigate('/preprocessing')} className="btn-primary">
              Proximo: Pre-processar <ChevronRight size={16} />
            </button>
          </motion.div>
        )}

        {state?.error && (
          <div className="flex items-center gap-3 bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 text-sm">
            <AlertCircle size={18} />
            {state.error}
          </div>
        )}

        {/* Loading state */}
        {!state && (
          <div className="card text-center text-gray-500 text-sm py-8">
            Aguardando inicio do scraping...
          </div>
        )}

      </div>
    </Layout>
  )
}
