import { useEffect, useState } from 'react'
import { DollarSign, X, TrendingUp, Clock } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import api from '../lib/api'

interface CostEntry {
  ts: number; model: string; phase: string
  tokens_in: number; tokens_out: number; cost_usd: number
}
interface CostEstimate {
  accumulated_usd: number
  preprocessing_estimate_usd: number
  total_estimate_usd: number
  by_phase: Record<string, number>
  phase_labels: Record<string, string>
}

const fmt     = (n: number) => `$${n.toFixed(4)}`
const fmtTime = (ts: number) =>
  new Date(ts * 1000).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })

export default function CostPanel() {
  const [open, setOpen]       = useState(false)
  const [data, setData]       = useState<CostEstimate | null>(null)
  const [history, setHistory] = useState<CostEntry[]>([])

  useEffect(() => {
    const load = () => {
      api.get<CostEstimate>('/api/costs/estimate').then(r => setData(r.data)).catch(() => {})
      api.get<CostEntry[]>('/api/costs/history').then(r => setHistory(r.data)).catch(() => {})
    }
    load()
    const id = setInterval(load, 10000)
    return () => clearInterval(id)
  }, [])

  const total = data?.accumulated_usd ?? 0

  return (
    <>
      {/* Floating button */}
      <button
        onClick={() => setOpen(v => !v)}
        className="fixed bottom-5 right-5 z-50 flex items-center gap-2 px-3 py-2
                   bg-white border border-surface-300 shadow-card-md
                   text-[10px] font-bold uppercase tracking-wider text-gray-700 hover:bg-surface-50 transition-colors"
      >
        <DollarSign size={13} className="text-accent-500" />
        {fmt(total)}
      </button>

      {/* Side panel */}
      <AnimatePresence>
        {open && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              onClick={() => setOpen(false)}
              className="fixed inset-0 z-40 bg-black/10"
            />
            {/* Panel */}
            <motion.div
              initial={{ x: 340 }} animate={{ x: 0 }} exit={{ x: 340 }}
              transition={{ type: 'spring', stiffness: 300, damping: 30 }}
              className="fixed right-0 top-0 bottom-0 w-80 z-50 bg-white border-l border-surface-200 flex flex-col shadow-card-md"
            >
              {/* Header */}
              <div className="h-12 flex items-center justify-between px-4 border-b border-surface-200 flex-shrink-0">
                <div className="flex items-center gap-2">
                  <DollarSign size={14} className="text-accent-500" />
                  <span className="text-sm font-semibold text-gray-900">Custos OpenAI</span>
                </div>
                <button onClick={() => setOpen(false)} className="btn-ghost p-1">
                  <X size={14} />
                </button>
              </div>

              <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin">
                {/* Total */}
                <div className="card-sm space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="section-title mb-0">Total acumulado</span>
                    <span className="text-lg font-bold text-accent-500 font-mono">{fmt(total)}</span>
                  </div>
                  {data && data.preprocessing_estimate_usd > 0 && (
                    <div className="border-t border-surface-200 pt-2 space-y-1">
                      <div className="flex justify-between text-xs text-gray-500">
                        <span className="flex items-center gap-1">
                          <TrendingUp size={10} /> Estimativa pre-proc
                        </span>
                        <span className="font-mono">{fmt(data.preprocessing_estimate_usd)}</span>
                      </div>
                      <div className="flex justify-between text-xs font-semibold text-gray-700">
                        <span>Estimativa total</span>
                        <span className="font-mono">{fmt(data.total_estimate_usd)}</span>
                      </div>
                    </div>
                  )}
                </div>

                {/* By phase */}
                {data && Object.keys(data.by_phase).length > 0 && (
                  <div className="card-sm space-y-2">
                    <p className="section-title mb-2">Por fase</p>
                    {Object.entries(data.by_phase).map(([phase, cost]) => (
                      <div key={phase} className="flex justify-between text-xs">
                        <span className="text-gray-600">{data.phase_labels[phase] ?? phase}</span>
                        <span className="font-mono text-gray-800">{fmt(cost)}</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Pricing table */}
                <div className="card-sm space-y-1.5">
                  <p className="section-title mb-2">Tabela de precos (2026)</p>
                  {[
                    { model: 'gpt-5.1',      inp: '$5.00',  out: '$20.00' },
                    { model: 'gpt-4o',       inp: '$2.50',  out: '$10.00' },
                    { model: 'gpt-4o-mini',  inp: '$0.15',  out: '$0.60'  },
                    { model: 'gpt-4.1',      inp: '$2.00',  out: '$8.00'  },
                    { model: 'gpt-4.1-mini', inp: '$0.40',  out: '$1.60'  },
                    { model: 'gpt-4.1-nano', inp: '$0.10',  out: '$0.40'  },
                    { model: 'o4-mini',      inp: '$1.10',  out: '$4.40'  },
                    { model: 'o3',           inp: '$10.00', out: '$40.00' },
                  ].map(r => (
                    <div key={r.model}
                      className="grid grid-cols-3 text-[10px] text-gray-500 border-b border-surface-100 pb-1">
                      <span className="font-mono text-gray-700">{r.model}</span>
                      <span className="text-center">{r.inp}/1M in</span>
                      <span className="text-right">{r.out}/1M out</span>
                    </div>
                  ))}
                </div>

                {/* Call history */}
                {history.length > 0 ? (
                  <div className="card-sm space-y-1.5">
                    <p className="section-title mb-2">Historico ({history.length} chamadas)</p>
                    {[...history].reverse().slice(0, 15).map((e, i) => (
                      <div key={i}
                        className="grid grid-cols-[auto_1fr_auto] gap-1 text-[10px] text-gray-500 border-b border-surface-100 pb-1">
                        <span className="flex items-center gap-0.5 text-gray-400">
                          <Clock size={9} />{fmtTime(e.ts)}
                        </span>
                        <span className="font-mono text-gray-600 truncate">{e.phase} / {e.model}</span>
                        <span className="font-mono text-gray-700">{fmt(e.cost_usd)}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-gray-400 text-center py-4">
                    Nenhuma chamada registrada ainda
                  </p>
                )}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  )
}
