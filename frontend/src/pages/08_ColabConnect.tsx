import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Monitor, Upload, Cpu, Play, ChevronRight, CheckCircle } from 'lucide-react'
import { motion } from 'framer-motion'
import Layout from '../components/Layout'
import { useWizard } from '../context/WizardContext'
import api from '../lib/api'

const CHECKLIST = [
  { id: 'browser',  icon: Monitor,  label: 'Abrindo Google Colab no browser...' },
  { id: 'login',    icon: CheckCircle, label: 'Verificando login Google...' },
  { id: 'upload',   icon: Upload,   label: 'Fazendo upload do notebook...' },
  { id: 'gpu',      icon: Cpu,      label: 'Configurando runtime GPU (T4)...' },
  { id: 'run',      icon: Play,     label: 'Iniciando execucao das celulas...' },
]

export default function ColabConnect() {
  const { state, setCurrentStep } = useWizard()
  const navigate = useNavigate()
  const [started, setStarted] = useState(false)
  const [starting, setStarting] = useState(false)
  const [generatedPath, setGeneratedPath] = useState('')
  const [activeStepIdx, setActiveStepIdx] = useState(-1)

  useEffect(() => { setCurrentStep(8) }, [setCurrentStep])

  // Simulate checklist steps once started
  useEffect(() => {
    if (!started) return
    let i = 0
    const interval = setInterval(() => {
      setActiveStepIdx(i)
      i++
      if (i >= CHECKLIST.length) clearInterval(interval)
    }, 2500)
    return () => clearInterval(interval)
  }, [started])

  async function handleStart() {
    setStarting(true)
    try {
      const res = await api.post<{ ok: boolean; notebook_path: string }>('/api/colab/start', {
        model_id: state.selectedModel || 'llama-3.2-3b',
        topic_profile: state.topicProfile ?? {},
      })
      setGeneratedPath(res.data.notebook_path)
      setStarted(true)
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } }
      alert(e.response?.data?.detail ?? 'Erro ao iniciar automacao Colab')
    } finally {
      setStarting(false)
    }
  }

  return (
    <Layout title="Colab - Treinamento" subtitle="Abrindo Google Colab automaticamente para fine-tuning">
      <div className="max-w-2xl space-y-6">

        {!started ? (
          <>
            {/* Info card */}
            <div className="card space-y-4">
              <h3 className="font-semibold text-gray-900">O que vai acontecer</h3>
              <div className="space-y-3">
                {[
                  {
                    icon: Monitor,
                    title: 'Browser visivel',
                    desc: 'Um navegador Chromium sera aberto. Voce vera tudo em tempo real e pode intervir a qualquer momento.',
                  },
                  {
                    icon: Upload,
                    title: 'Notebook gerado automaticamente',
                    desc: 'Um notebook .ipynb com todo o codigo de fine-tuning sera gerado e carregado no Colab.',
                  },
                  {
                    icon: Cpu,
                    title: 'GPU gratuita (T4)',
                    desc: 'O Colab free tier oferece ~4h de GPU T4 por sessao — suficiente para fine-tuning de modelos pequenos.',
                  },
                ].map(item => (
                  <div key={item.title} className="flex gap-3">
                    <div className="w-8 h-8 rounded-lg bg-accent-500/10 flex items-center justify-center flex-shrink-0">
                      <item.icon size={16} className="text-accent-500" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-800">{item.title}</p>
                      <p className="text-xs text-gray-500 mt-0.5">{item.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Warning */}
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-800">
              <p className="font-medium mb-1">Antes de continuar:</p>
              <ul className="space-y-1 text-xs list-disc list-inside">
                <li>Certifique-se de estar logado em sua conta Google no browser</li>
                <li>O Colab free tier tem limite de ~4h de GPU por sessao</li>
                <li>O modelo: <span className="font-mono font-medium">{state.selectedModel || 'llama-3.2-3b'}</span></li>
              </ul>
            </div>

            <div className="flex justify-end">
              <button onClick={handleStart} disabled={starting} className="btn-primary px-8">
                {starting ? 'Preparando...' : 'Iniciar Treinamento no Colab'}
                <ChevronRight size={16} />
              </button>
            </div>
          </>
        ) : (
          <>
            {/* Checklist animado */}
            <div className="card space-y-3">
              <p className="text-sm font-medium text-gray-700">Automacao em progresso</p>
              {CHECKLIST.map((item, i) => {
                const done = i < activeStepIdx
                const active = i === activeStepIdx
                const Icon = item.icon
                return (
                  <motion.div
                    key={item.id}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: i <= activeStepIdx ? 1 : 0.35, x: 0 }}
                    transition={{ delay: i * 0.1 }}
                    className="flex items-center gap-3"
                  >
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 transition-colors
                      ${done ? 'bg-green-100' : active ? 'bg-accent-500' : 'bg-surface-100'}`}>
                      {done
                        ? <CheckCircle size={16} className="text-green-600" />
                        : <Icon size={16} className={active ? 'text-white' : 'text-gray-400'} />
                      }
                    </div>
                    <div className="flex-1">
                      <p className={`text-sm ${active ? 'font-medium text-gray-900' : done ? 'text-gray-500' : 'text-gray-400'}`}>
                        {item.label}
                      </p>
                      {active && (
                        <motion.div className="flex gap-1 mt-1">
                          {[0,1,2].map(j => (
                            <motion.span key={j} className="w-1 h-1 bg-accent-500 rounded-full"
                              animate={{ opacity: [0.3, 1, 0.3] }}
                              transition={{ repeat: Infinity, duration: 1, delay: j * 0.2 }}
                            />
                          ))}
                        </motion.div>
                      )}
                    </div>
                  </motion.div>
                )
              })}
            </div>

            {/* Instructions for user */}
            <div className="card bg-blue-50 border-blue-200 space-y-3">
              <p className="text-sm font-semibold text-blue-800">Acoes necessarias no browser aberto:</p>
              <ol className="text-xs text-blue-700 space-y-1.5 list-decimal list-inside">
                <li>Faca login na sua conta Google se solicitado</li>
                <li>No Colab: File → Upload notebook → selecione <span className="font-mono bg-blue-100 px-1 rounded">generated_notebook.ipynb</span></li>
                <li>Configure o runtime: Runtime → Change runtime type → T4 GPU</li>
                <li>Execute tudo: Runtime → Run all (Ctrl+F9)</li>
                <li>Na celula de upload, faca upload do arquivo <span className="font-mono bg-blue-100 px-1 rounded">training_data.jsonl</span></li>
                <li>Aguarde o treinamento e faca download do <span className="font-mono bg-blue-100 px-1 rounded">modelo_final.gguf</span></li>
              </ol>
              {generatedPath && (
                <p className="text-xs text-blue-600 font-mono bg-blue-100 p-2 rounded">
                  Notebook: {generatedPath}
                </p>
              )}
            </div>

            <div className="flex justify-end">
              <button onClick={() => navigate('/training')} className="btn-primary px-8">
                Monitorar Treinamento <ChevronRight size={16} />
              </button>
            </div>
          </>
        )}

      </div>
    </Layout>
  )
}
