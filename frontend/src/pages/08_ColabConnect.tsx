import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Monitor, Upload, Cpu, Play, ArrowRight, CheckCircle2, Info } from 'lucide-react'
import { motion } from 'framer-motion'
import Layout from '../components/Layout'
import { useWizard } from '../context/WizardContext'
import api from '../lib/api'

const STEPS = [
  { icon: Monitor, label: 'Abrindo Google Colab...' },
  { icon: CheckCircle2, label: 'Verificando login...' },
  { icon: Upload, label: 'Fazendo upload do notebook...' },
  { icon: Cpu, label: 'Configurando runtime GPU (T4)...' },
  { icon: Play, label: 'Iniciando execucao das celulas...' },
]

export default function ColabConnect() {
  const { state, setCurrentStep } = useWizard()
  const navigate = useNavigate()
  const [started, setStarted]     = useState(false)
  const [starting, setStarting]   = useState(false)
  const [notebookPath, setNbPath] = useState('')
  const [activeIdx, setActiveIdx] = useState(-1)

  useEffect(() => { setCurrentStep(8) }, [setCurrentStep])

  useEffect(() => {
    if (!started) return
    let i = 0
    const t = setInterval(() => { setActiveIdx(i); i++; if (i >= STEPS.length) clearInterval(t) }, 2500)
    return () => clearInterval(t)
  }, [started])

  async function start() {
    setStarting(true)
    try {
      const res = await api.post<{ ok: boolean; notebook_path: string }>('/api/colab/start', {
        model_id: state.selectedModel || 'llama-3.2-3b',
        topic_profile: state.topicProfile ?? {},
      })
      setNbPath(res.data.notebook_path)
      setStarted(true)
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } }
      alert(e.response?.data?.detail ?? 'Erro ao iniciar Colab')
    } finally { setStarting(false) }
  }

  return (
    <Layout title="Colab — Treinamento" subtitle="Automacao via Playwright para fine-tuning no Google Colab">
      <div className="max-w-xl space-y-4">

        {!started ? (
          <>
            <div className="card space-y-4">
              <h3 className="text-sm font-semibold text-gray-900 border-b border-surface-200 pb-2">
                O que vai acontecer
              </h3>
              {[
                { icon: Monitor, title: 'Browser visivel',        desc: 'Um Chromium sera aberto. Voce acompanha tudo e pode intervir.' },
                { icon: Upload,  title: 'Notebook automatico',    desc: 'Codigo de fine-tuning gerado e carregado no Colab automaticamente.' },
                { icon: Cpu,     title: 'GPU gratuita T4',        desc: 'Colab free tier: ~4h de GPU T4 por sessao. Suficiente para modelos pequenos.' },
              ].map(item => (
                <div key={item.title} className="flex gap-3">
                  <div className="w-7 h-7 rounded border border-surface-200 bg-surface-50 flex items-center justify-center flex-shrink-0">
                    <item.icon size={14} className="text-accent-500" />
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-gray-800">{item.title}</p>
                    <p className="text-[11px] text-gray-500 mt-0.5">{item.desc}</p>
                  </div>
                </div>
              ))}
            </div>

            <div className="flex items-start gap-2 bg-warning-50 border border-yellow-200 rounded p-3 text-xs text-warning-600">
              <Info size={13} className="mt-0.5 flex-shrink-0" />
              <div>
                Modelo selecionado: <span className="font-mono font-semibold">{state.selectedModel || 'llama-3.2-3b'}</span>.
                Certifique-se de estar logado no Google no browser padrao.
              </div>
            </div>

            <div className="flex justify-end">
              <button onClick={start} disabled={starting} className="btn-primary">
                {starting ? 'Preparando...' : 'Iniciar Treinamento no Colab'}
                <ArrowRight size={14} />
              </button>
            </div>
          </>
        ) : (
          <>
            {/* Checklist */}
            <div className="card space-y-2">
              <p className="section-title mb-3">Progresso da automacao</p>
              {STEPS.map((step, i) => {
                const done   = i < activeIdx
                const active = i === activeIdx
                const Icon   = step.icon
                return (
                  <motion.div key={i} initial={{ opacity: 0.3 }} animate={{ opacity: i <= activeIdx ? 1 : 0.3 }}
                    className="flex items-center gap-2.5">
                    <div className={`w-7 h-7 rounded border flex items-center justify-center flex-shrink-0 transition-colors
                      ${done   ? 'bg-success-50 border-green-200' : ''}
                      ${active ? 'bg-accent-500 border-accent-500' : ''}
                      ${!done && !active ? 'bg-surface-50 border-surface-200' : ''}`}>
                      {done
                        ? <CheckCircle2 size={14} className="text-success-600" />
                        : <Icon size={14} className={active ? 'text-white' : 'text-gray-400'} />
                      }
                    </div>
                    <span className={`text-xs ${active ? 'font-semibold text-gray-900' : done ? 'text-gray-500' : 'text-gray-400'}`}>
                      {step.label}
                    </span>
                    {active && (
                      <motion.span className="w-1.5 h-1.5 bg-accent-500 rounded-sm ml-1"
                        animate={{ opacity: [1, 0.3, 1] }}
                        transition={{ repeat: Infinity, duration: 1 }} />
                    )}
                  </motion.div>
                )
              })}
            </div>

            {/* Manual instructions */}
            <div className="card-sm space-y-2">
              <p className="section-title mb-2">Acoes no browser aberto</p>
              {[
                'Faca login na conta Google se solicitado',
                <>File → Upload notebook → selecione <span className="code">generated_notebook.ipynb</span></>,
                'Runtime → Change runtime type → T4 GPU',
                'Runtime → Run all (Ctrl+F9)',
                <>Na celula de upload, selecione <span className="code">training_data.jsonl</span></>,
                <>Aguarde o fim e faca download do <span className="code">modelo_final.gguf</span></>,
              ].map((s, i) => (
                <div key={i} className="flex gap-2 text-xs text-gray-600">
                  <span className="w-4 h-4 rounded-sm bg-surface-200 text-gray-500 flex items-center justify-center text-[10px] font-bold flex-shrink-0">{i+1}</span>
                  <span>{s}</span>
                </div>
              ))}
              {notebookPath && (
                <p className="text-[11px] text-gray-400 font-mono mt-2 border-t border-surface-200 pt-2">
                  Notebook: {notebookPath}
                </p>
              )}
            </div>

            <div className="flex justify-end">
              <button onClick={() => navigate('/training')} className="btn-primary">
                Monitorar Treinamento <ArrowRight size={14} />
              </button>
            </div>
          </>
        )}
      </div>
    </Layout>
  )
}
