import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Monitor, Upload, Cpu, Play, ArrowRight, ArrowLeft, CheckCircle2, Info, Terminal, Laptop, FileUp } from 'lucide-react'
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
  { icon: FileUp,        label: 'Injetando dataset de treinamento...' },
]

const STEP_LABELS = [
  'Abrindo Google Colab...',
  'Verificando login...',
  'Fazendo upload do notebook...',
  'Configurando runtime GPU',
  'Iniciando execucao das celulas...',
  'Injetando dataset de treinamento...',
]

interface HyperParams {
  training_target:             string
  training_target_reason:      string
  quantization:                string
  lora_r:                      number
  lora_alpha:                  number
  batch_size:                  number
  gradient_accumulation_steps: number
  max_seq_length:              number
  num_epochs:                  number
  learning_rate:               number
  use_flash_attention:         boolean
  gradient_checkpointing:      boolean
  gguf_quantization_type:      string
  justification:               string
  training_feasible:           boolean
  target_modules:              string[]
}

// Scanning-line loader (design system)
function ScanLoader({ label }: { label: string }) {
  return (
    <div className="card flex flex-col items-center gap-4 py-8">
      <div className="relative w-48 h-10 border border-surface-300 bg-surface-50 overflow-hidden">
        <motion.div
          className="absolute top-0 left-0 w-full h-0.5 bg-accent-500 opacity-80"
          animate={{ y: [0, 40, 0] }}
          transition={{ repeat: Infinity, duration: 1.6, ease: 'linear' }}
        />
        <motion.div
          className="absolute top-0 left-0 w-full h-6 bg-accent-500 opacity-[0.04]"
          animate={{ y: [0, 40, 0] }}
          transition={{ repeat: Infinity, duration: 1.6, ease: 'linear' }}
        />
      </div>
      <p className="font-display text-[10px] font-bold uppercase tracking-[0.08em] text-gray-500">{label}</p>
    </div>
  )
}

export default function ColabConnect() {
  const { state, update, setCurrentStep } = useWizard()
  const navigate = useNavigate()

  // Restaurar estado persistido do contexto
  const [started, setStarted]   = useState(state.colabStarted)
  const [starting, setStarting] = useState(false)
  const [params, setParams]     = useState<HyperParams | null>(
    state.colabParams as HyperParams | null
  )
  const [target, setTarget]     = useState<'local' | 'colab' | null>(
    (state.colabTarget as 'local' | 'colab') || null
  )
  const [scriptPath, setScriptPath] = useState(state.colabScriptPath)
  const [notebookPath, setNbPath]   = useState(state.colabNotebookPath)
  const [datasetInjected, setDatasetInjected] = useState(false)
  const [tsStep, setTsStep] = useState('')

  useEffect(() => { setCurrentStep(8) }, [setCurrentStep])

  // SSE — reconecta automaticamente ao recarregar se automação ainda rodando
  useEffect(() => {
    if (!started || target !== 'colab') return
    const es = new EventSource('http://localhost:8000/api/colab/status')
    es.onmessage = e => {
      const d = JSON.parse(e.data)
      setTsStep(d.step ?? '')
      if (d.dataset_injected) setDatasetInjected(true)
      if (d.finished || d.error) es.close()
    }
    es.onerror = () => es.close()
    return () => es.close()
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

      const { params: p, target: t, notebook_path, script_path } = res.data

      setParams(p)
      setTarget(t)
      if (notebook_path) setNbPath(notebook_path)
      if (script_path)   setScriptPath(script_path)
      setStarted(true)

      // Persistir no contexto para sobreviver à navegação
      update({
        colabParams:       p as unknown as Record<string, unknown>,
        colabTarget:       t,
        colabStarted:      true,
        colabNotebookPath: notebook_path ?? '',
        colabScriptPath:   script_path   ?? '',
      })
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } }
      alert(e.response?.data?.detail ?? 'Erro ao iniciar treinamento')
    } finally { setStarting(false) }
  }

  const rawIdx = STEP_LABELS.findIndex(s => tsStep.startsWith(s.slice(0, 15)))
  // Se step ultrapassou os rastreados (ex: "Treinando no Colab..."), marcar todos como feitos
  const activeIdx = rawIdx === -1 && tsStep ? STEP_LABELS.length : rawIdx

  const ParamRow = ({ label, value }: { label: string; value: string | number | boolean }) => (
    <div className="flex justify-between text-xs border-b border-surface-100 py-1">
      <span className="data-label">{label}</span>
      <span className="font-mono text-gray-800">{String(value)}</span>
    </div>
  )

  return (
    <Layout title="Treinamento" subtitle="Hiperparametros gerados por GPT-5.1 — Dr. Alex Chen">
      <div className="max-w-xl space-y-4">

        {starting ? (
          <ScanLoader label="Consultando GPT-5.1 — Dr. Alex Chen..." />
        ) : !started ? (
          <>
            <div className="card space-y-4">
              <h3 className="font-display text-[11px] font-bold text-gray-900 uppercase tracking-[0.08em] border-b border-surface-200 pb-2">
                O que vai acontecer
              </h3>
              {[
                { icon: Cpu,     title: 'Hiperparametros por IA',   desc: 'GPT-5.1 vai calcular todos os parametros de treinamento com base no seu hardware exato.' },
                { icon: Monitor, title: 'GPU local ou Colab T4',    desc: 'Se sua GPU superar o T4 (15GB VRAM), o treinamento e feito na sua maquina. Caso contrario, vai pro Colab.' },
                { icon: Upload,  title: 'Notebook/Script gerado',   desc: 'Um notebook Colab ou script Python e gerado automaticamente com a config da IA.' },
              ].map(item => (
                <div key={item.title} className="flex gap-3">
                  <div className="w-7 h-7 border border-surface-200 bg-surface-50 flex items-center justify-center flex-shrink-0">
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
              <button onClick={start} className="btn-primary">
                Gerar Hiperparametros e Iniciar <ArrowRight size={14} />
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
                  'Login automatico via cookies salvos (ou manual na primeira vez)',
                  'Upload do notebook, GPU T4 e Run All sao automaticos',
                  'Dataset embutido no notebook — sem upload manual necessario',
                  'Download do modelo GGUF detectado ao finalizar',
                  <>Apos a primeira vez, tudo roda em <span className="code">headless</span> (sem tela)</>,
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

            <div className="flex justify-between items-center">
              <button
                onClick={() => {
                  // Permite reiniciar se necessário
                  update({ colabStarted: false, colabParams: null, colabTarget: '' })
                  setStarted(false)
                  setParams(null)
                  setTarget(null)
                }}
                className="btn-secondary text-[10px]"
              >
                Regenerar hiperparametros
              </button>
              <button
                onClick={() => navigate('/training')}
                className="btn-primary"
                disabled={target === 'colab' && !datasetInjected}
                title={target === 'colab' && !datasetInjected ? 'Aguardando injecao do dataset...' : ''}
              >
                {target === 'colab' && !datasetInjected
                  ? 'Aguardando dataset...'
                  : 'Monitorar Treinamento'
                }
                {(target !== 'colab' || datasetInjected) && <ArrowRight size={14} />}
              </button>
            </div>
          </>
        )}
      </div>
    </Layout>
  )
}
