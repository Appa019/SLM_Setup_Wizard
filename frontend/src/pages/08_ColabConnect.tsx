import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Monitor, Upload, Cpu, Play, ArrowRight, ArrowLeft, CheckCircle2, Info, Terminal, Laptop } from 'lucide-react'
import { motion } from 'framer-motion'
import Layout from '../components/Layout'
import { useWizard } from '../context/WizardContext'
import api from '../lib/api'

const STEPS = [
  { icon: Monitor,       label: 'Abrindo Google Colab...' },
  { icon: CheckCircle2,  label: 'Verificando login...' },
  { icon: Upload,        label: 'Fazendo upload do notebook...' },
  { icon: Cpu,           label: 'Configurando runtime GPU (T4)...' },
  { icon: Play,          label: 'Iniciando execucao das celulas...' },
]

interface HyperParams {
  training_target:           string
  training_target_reason:    string
  quantization:              string
  lora_r:                    number
  lora_alpha:                number
  batch_size:                number
  gradient_accumulation_steps: number
  max_seq_length:            number
  num_epochs:                number
  learning_rate:             number
  use_flash_attention:       boolean
  gradient_checkpointing:    boolean
  gguf_quantization_type:    string
  justification:             string
  training_feasible:         boolean
  target_modules:            string[]
}

export default function ColabConnect() {
  const { state, setCurrentStep } = useWizard()
  const navigate = useNavigate()

  const [started, setStarted]   = useState(false)
  const [starting, setStarting] = useState(false)
  const [activeIdx, setActiveIdx] = useState(-1)
  const [params, setParams]     = useState<HyperParams | null>(null)
  const [target, setTarget]     = useState<'local' | 'colab' | null>(null)
  const [scriptPath, setScriptPath] = useState('')
  const [notebookPath, setNbPath]   = useState('')

  useEffect(() => { setCurrentStep(8) }, [setCurrentStep])

  useEffect(() => {
    if (!started || target !== 'colab') return
    let i = 0
    const t = setInterval(() => { setActiveIdx(i); i++; if (i >= STEPS.length) clearInterval(t) }, 2500)
    return () => clearInterval(t)
  }, [started, target])

  async function start() {
    setStarting(true)
    try {
      const res = await api.post<{
        ok: boolean
        target: 'local' | 'colab'
        notebook_path?: string
        script_path?: string
        params: HyperParams
      }>('/api/colab/start', {
        model_id:      state.selectedModel || 'llama-3.2-3b',
        quant_type:    state.selectedQuant  || 'q4_k_m',
        hf_id:         state.selectedHfId  ?? '',
        topic_profile: state.topicProfile   ?? {},
        hardware:      state.hardware       ?? {},
      })
      setParams(res.data.params)
      setTarget(res.data.target)
      if (res.data.notebook_path) setNbPath(res.data.notebook_path)
      if (res.data.script_path)   setScriptPath(res.data.script_path)
      setStarted(true)
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } }
      alert(e.response?.data?.detail ?? 'Erro ao iniciar treinamento')
    } finally { setStarting(false) }
  }

  const ParamRow = ({ label, value }: { label: string; value: string | number | boolean }) => (
    <div className="flex justify-between text-xs border-b border-surface-100 py-1">
      <span className="text-gray-400">{label}</span>
      <span className="font-mono text-gray-800">{String(value)}</span>
    </div>
  )

  return (
    <Layout title="Treinamento" subtitle="Hiperparametros gerados por GPT-5.1 — Dr. Alex Chen">
      <div className="max-w-xl space-y-4">

        {!started ? (
          <>
            <div className="card space-y-4">
              <h3 className="text-sm font-semibold text-gray-900 border-b border-surface-200 pb-2">
                O que vai acontecer
              </h3>
              {[
                { icon: Cpu,     title: 'Hiperparametros por IA',   desc: 'GPT-5.1 vai calcular todos os parametros de treinamento com base no seu hardware exato.' },
                { icon: Monitor, title: 'GPU local ou Colab T4',    desc: 'Se sua GPU superar o T4 (15GB VRAM), o treinamento e feito na sua maquina. Caso contrario, vai pro Colab.' },
                { icon: Upload,  title: 'Notebook/Script gerado',   desc: 'Um notebook Colab ou script Python e gerado automaticamente com a config da IA.' },
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
                Modelo: <span className="font-mono font-semibold">{state.selectedModel || 'llama-3.2-3b'}</span> ·
                Variante: <span className="font-mono font-semibold">{state.selectedQuant || 'q4_k_m'}</span> ·
                VRAM usuario: <span className="font-mono font-semibold">{state.hardware?.vram_gb ?? 'N/A'} GB</span>
              </div>
            </div>

            <div className="flex justify-between items-center">
              <button onClick={() => navigate('/preprocessing')} className="btn-secondary">
                <ArrowLeft size={14} /> Voltar
              </button>
              <button onClick={start} disabled={starting} className="btn-primary">
                {starting ? 'Consultando GPT-5.1...' : 'Gerar Hiperparametros e Iniciar'}
                <ArrowRight size={14} />
              </button>
            </div>
          </>
        ) : (
          <>
            {/* Target badge */}
            {target && (
              <div className={`flex items-center gap-2 p-3 rounded border text-xs font-semibold
                ${target === 'local'
                  ? 'bg-accent-50 border-accent-300 text-accent-700'
                  : 'bg-success-50 border-green-200 text-success-700'}`}>
                {target === 'local' ? <Laptop size={14} /> : <Monitor size={14} />}
                {target === 'local'
                  ? 'Treinamento LOCAL — sua GPU supera o T4'
                  : 'Treinamento COLAB — usando GPU T4 gratuita'}
              </div>
            )}

            {/* Hyperparams card */}
            {params && (
              <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
                className="card-sm space-y-1">
                <div className="flex items-center gap-1.5 section-title mb-3">
                  <Terminal size={11} /> Configuracao gerada pelo GPT-5.1
                </div>
                <ParamRow label="Quantizacao"         value={params.quantization} />
                <ParamRow label="LoRA r"              value={params.lora_r} />
                <ParamRow label="LoRA alpha"          value={params.lora_alpha} />
                <ParamRow label="Batch size"          value={params.batch_size} />
                <ParamRow label="Grad accumulation"   value={params.gradient_accumulation_steps} />
                <ParamRow label="Seq length"          value={params.max_seq_length} />
                <ParamRow label="Epochs"              value={params.num_epochs} />
                <ParamRow label="Learning rate"       value={params.learning_rate} />
                <ParamRow label="Flash Attention"     value={params.use_flash_attention} />
                <ParamRow label="Grad checkpointing"  value={params.gradient_checkpointing} />
                <ParamRow label="GGUF output"         value={params.gguf_quantization_type} />
                {params.justification && (
                  <div className="border-t border-surface-200 pt-2 mt-1">
                    <p className="text-[10px] text-gray-500 italic leading-relaxed">{params.justification}</p>
                  </div>
                )}
              </motion.div>
            )}

            {/* Colab steps */}
            {target === 'colab' && (
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
            )}

            {/* Local training instructions */}
            {target === 'local' && (
              <div className="card-sm space-y-2">
                <p className="section-title mb-2">Script gerado — execute localmente</p>
                {[
                  <>Instale as deps: <span className="code">pip install -r colab/requirements.txt</span></>,
                  <>Execute o script: <span className="code">python colab/local_training.py</span></>,
                  'Aguarde o treinamento concluir (pode levar horas)',
                  <>Converta para GGUF conforme instrucoes no final do script</>,
                  <>Copie o <span className="code">modelo_final.gguf</span> para a pasta <span className="code">models/</span></>,
                ].map((s, i) => (
                  <div key={i} className="flex gap-2 text-xs text-gray-600">
                    <span className="w-4 h-4 rounded-sm bg-surface-200 text-gray-500 flex items-center justify-center text-[10px] font-bold flex-shrink-0">{i+1}</span>
                    <span>{s}</span>
                  </div>
                ))}
                {scriptPath && (
                  <p className="text-[11px] text-gray-400 font-mono mt-2 border-t border-surface-200 pt-2">
                    Script: {scriptPath}
                  </p>
                )}
              </div>
            )}

            {/* Colab manual instructions */}
            {target === 'colab' && (
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
            )}

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
