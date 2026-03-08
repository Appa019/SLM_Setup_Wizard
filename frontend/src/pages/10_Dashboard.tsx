import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Cpu, FolderOpen, Play, Square, Send, RefreshCw, CheckCircle2, AlertCircle, Terminal, Plus, ArrowLeft } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import Layout from '../components/Layout'
import ChatMessage from '../components/ChatMessage'
import { useWizard } from '../context/WizardContext'
import api from '../lib/api'

interface ModelInfo {
  name:            string
  path:            string
  size_gb:         number
  topic:           string
  base_model:      string
  quant_type:      string
  training_target: string
  created_at:      string
  subtopics:       string[]
}

interface ModelStatus {
  llama_available: boolean
  models:          ModelInfo[]
  server_running:  boolean
  loaded_model:    string
  server_port:     number | null
}

interface Msg { role: 'user' | 'assistant'; content: string }

export default function Dashboard() {
  const { setCurrentStep, resetWizard } = useWizard()
  const navigate = useNavigate()
  const [status, setStatus]     = useState<ModelStatus | null>(null)
  const [selected, setSelected] = useState('')
  const [loading, setLoading]   = useState(false)
  const [stopping, setStopping] = useState(false)

  // Chat
  const [messages, setMessages] = useState<Msg[]>([])
  const [input, setInput]       = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    setCurrentStep(10)
    fetchStatus()
  }, [setCurrentStep])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function fetchStatus() {
    api.get<ModelStatus>('/api/training/status').then(r => {
      setStatus(r.data)
      if (r.data.loaded_model) setSelected(r.data.loaded_model)
      else if (r.data.models.length > 0) setSelected(r.data.models[0].name)
    }).catch(() => {})
  }

  async function handleLoad() {
    if (!selected) return
    setLoading(true)
    try {
      await api.post('/api/training/load', { model_name: selected })
      await fetchStatus()
      setMessages([{
        role: 'assistant',
        content: `Modelo "${selected}" carregado. Pode comecar a conversar!`,
      }])
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } }
      alert(e.response?.data?.detail ?? 'Erro ao carregar modelo')
    } finally { setLoading(false) }
  }

  async function handleStop() {
    setStopping(true)
    try { await api.post('/api/training/stop'); await fetchStatus(); setMessages([]) }
    catch { /* ignore */ }
    finally { setStopping(false) }
  }

  async function sendMessage() {
    const text = input.trim()
    if (!text || chatLoading) return
    setInput('')

    const userMsg: Msg = { role: 'user', content: text }
    const history = [...messages, userMsg]
    setMessages([...history, { role: 'assistant', content: '...' }])
    setChatLoading(true)

    try {
      const res = await api.post<{ response: string }>('/api/training/chat', {
        message: text,
        history: history.map(m => ({ role: m.role, content: m.content })),
      })
      setMessages(prev => {
        const u = [...prev]
        u[u.length - 1] = { role: 'assistant', content: res.data.response }
        return u
      })
    } catch {
      setMessages(prev => {
        const u = [...prev]
        u[u.length - 1] = { role: 'assistant', content: 'Erro ao consultar o modelo.' }
        return u
      })
    } finally { setChatLoading(false) }
  }

  const running = status?.server_running ?? false

  return (
    <Layout
      title="Dashboard"
      subtitle="Gerencie e teste seu modelo fine-tunado"
      actions={
        <button onClick={fetchStatus} className="btn-ghost text-xs">
          <RefreshCw size={13} /> Atualizar
        </button>
      }
    >
      <div className="max-w-2xl space-y-4">

        <div className="flex justify-start">
          <button onClick={() => navigate('/training')} className="btn-secondary text-xs">
            <ArrowLeft size={13} /> Voltar
          </button>
        </div>

        {/* llama.cpp status */}
        {status && !status.llama_available && (
          <div className="flex items-start gap-2 bg-warning-50 border border-yellow-200 rounded p-3 text-xs text-warning-600">
            <AlertCircle size={14} className="mt-0.5 flex-shrink-0" />
            <div>
              <p className="font-semibold">llama.cpp nao detectado</p>
              <p className="mt-0.5">Instale com: <span className="code">pip install llama-cpp-python</span> ou compile o llama.cpp e adicione ao PATH.</p>
            </div>
          </div>
        )}

        {/* Model selector + controls */}
        <div className="card space-y-4">
          <div className="flex items-center gap-2 border-b border-surface-200 pb-3">
            <Cpu size={15} className="text-accent-500" />
            <h2 className="font-semibold text-gray-900 text-sm">Controle do Modelo</h2>
            {running && (
              <span className="ml-auto badge-green flex items-center gap-1">
                <motion.span
                  className="w-1.5 h-1.5 bg-green-500 rounded-sm"
                  animate={{ opacity: [1, 0.3, 1] }}
                  transition={{ repeat: Infinity, duration: 1.5 }}
                />
                Rodando na porta {status?.server_port}
              </span>
            )}
          </div>

          {/* Model list */}
          {status?.models.length === 0 && (
            <div className="text-xs text-gray-400 flex items-center gap-1.5">
              <FolderOpen size={13} />
              Nenhum modelo .gguf encontrado em <span className="code">models/</span>.
              Faca o download apos o treinamento no Colab.
            </div>
          )}

          {status && status.models.length > 0 && (
            <div className="space-y-1.5">
              <p className="section-title">Especialistas treinados</p>
              {status.models.map(m => {
                const isLoaded   = status.loaded_model === m.name && running
                const isSelected = selected === m.name
                const dateStr    = m.created_at
                  ? new Date(m.created_at).toLocaleDateString('pt-BR')
                  : ''
                const targetBadge = m.training_target === 'local' ? 'badge-blue' : 'badge-gray'
                return (
                  <label
                    key={m.name}
                    className={`flex items-start gap-2.5 p-3 rounded border cursor-pointer transition-colors
                      ${isSelected
                        ? 'border-accent-500 bg-accent-50'
                        : 'border-surface-200 hover:border-surface-300'}`}
                  >
                    <input
                      type="radio" name="model" value={m.name}
                      checked={isSelected}
                      onChange={() => setSelected(m.name)}
                      className="accent-accent-500 mt-1 flex-shrink-0"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <p className="text-sm font-semibold text-gray-900 truncate">
                          {m.topic || m.name}
                        </p>
                        {isLoaded && <CheckCircle2 size={13} className="text-success-600 flex-shrink-0" />}
                      </div>
                      <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                        {m.base_model && <span className="code">{m.base_model}</span>}
                        {m.quant_type && <span className="code">{m.quant_type.toUpperCase()}</span>}
                        <span className="text-[11px] text-gray-400">{m.size_gb} GB</span>
                        {m.training_target && (
                          <span className={`${targetBadge} text-[10px]`}>
                            {m.training_target === 'local' ? 'GPU local' : 'Colab T4'}
                          </span>
                        )}
                        {dateStr && <span className="text-[11px] text-gray-400">{dateStr}</span>}
                      </div>
                      {m.subtopics && m.subtopics.length > 0 && (
                        <p className="text-[10px] text-gray-400 mt-0.5 truncate">
                          {m.subtopics.slice(0, 4).join(' · ')}
                        </p>
                      )}
                    </div>
                  </label>
                )
              })}
            </div>
          )}

          {/* Action buttons */}
          <div className="flex gap-2 border-t border-surface-200 pt-3 flex-wrap">
            <button
              onClick={handleLoad}
              disabled={!selected || loading || running}
              className="btn-primary"
            >
              <Play size={13} />
              {loading ? 'Carregando...' : 'Carregar Modelo'}
            </button>
            {running && (
              <button onClick={handleStop} disabled={stopping} className="btn-danger">
                <Square size={13} />
                {stopping ? 'Parando...' : 'Parar'}
              </button>
            )}
            <button
              onClick={() => { resetWizard(); navigate('/settings') }}
              className="btn-secondary ml-auto"
            >
              <Plus size={13} />
              Treinar Novo Especialista
            </button>
          </div>
        </div>

        {/* Chat test */}
        <AnimatePresence>
          {running && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="card space-y-3"
            >
              <div className="flex items-center gap-2 border-b border-surface-200 pb-3">
                <Terminal size={15} className="text-accent-500" />
                <h2 className="font-semibold text-gray-900 text-sm">Testar Modelo</h2>
                <span className="code ml-auto">{status?.loaded_model}</span>
              </div>

              {/* Messages */}
              <div className="h-64 overflow-y-auto scrollbar-thin py-1">
                {messages.length === 0 && (
                  <p className="text-xs text-gray-400 text-center mt-8">
                    Envie uma mensagem para testar o modelo fine-tunado
                  </p>
                )}
                {messages.map((msg, i) => (
                  <ChatMessage key={i} role={msg.role} content={msg.content} />
                ))}
                <div ref={bottomRef} />
              </div>

              {/* Input */}
              <div className="flex gap-2 border-t border-surface-200 pt-3">
                <input
                  type="text"
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && sendMessage()}
                  placeholder="Envie uma mensagem para o modelo..."
                  disabled={chatLoading}
                  className="input flex-1"
                />
                <button
                  onClick={sendMessage}
                  disabled={!input.trim() || chatLoading}
                  className="btn-primary px-3"
                >
                  <Send size={14} />
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Final summary */}
        {status && (
          <div className="card-sm">
            <p className="section-title mb-2">Resumo do projeto</p>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-gray-600">
              <div className="flex justify-between border-b border-surface-100 py-1">
                <span className="text-gray-400">llama.cpp</span>
                <span className={status.llama_available ? 'text-success-600 font-medium' : 'text-danger-600'}>
                  {status.llama_available ? 'Disponivel' : 'Nao instalado'}
                </span>
              </div>
              <div className="flex justify-between border-b border-surface-100 py-1">
                <span className="text-gray-400">Modelos</span>
                <span className="font-medium">{status.models.length} arquivo(s)</span>
              </div>
              <div className="flex justify-between border-b border-surface-100 py-1">
                <span className="text-gray-400">Servidor</span>
                <span className={running ? 'text-success-600 font-medium' : 'text-gray-500'}>
                  {running ? `Porta ${status.server_port}` : 'Parado'}
                </span>
              </div>
              <div className="flex justify-between border-b border-surface-100 py-1">
                <span className="text-gray-400">Modelo ativo</span>
                <span className="font-mono truncate max-w-[120px]">{status.loaded_model || '—'}</span>
              </div>
            </div>
          </div>
        )}

      </div>
    </Layout>
  )
}
