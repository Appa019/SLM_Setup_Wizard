import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Send, ArrowRight, ArrowLeft, CheckCircle2 } from 'lucide-react'
import { motion } from 'framer-motion'
import Layout from '../components/Layout'
import ChatMessage from '../components/ChatMessage'
import { useWizard } from '../context/WizardContext'
import api from '../lib/api'

interface Msg { role: 'user' | 'assistant'; content: string }

const WELCOME: Msg = {
  role: 'assistant',
  content:
    'Ola! Vou ajudar a definir o tema do seu modelo especializado.\n\n' +
    'Qual area de conhecimento voce quer que ele domine? Seja especifico — ' +
    '"direito trabalhista brasileiro", "suporte tecnico Linux" ou "receitas veganas" sao bons exemplos.',
}

export default function TopicChat() {
  const { update, setCurrentStep } = useWizard()
  const navigate = useNavigate()

  const [messages, setMessages]   = useState<Msg[]>([WELCOME])
  const [input, setInput]         = useState('')
  const [streaming, setStreaming] = useState(false)
  const [finalizing, setFinalizing] = useState(false)
  const [finalized, setFinalized] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef  = useRef<HTMLTextAreaElement>(null)

  useEffect(() => { setCurrentStep(4) }, [setCurrentStep])
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  async function send() {
    const text = input.trim()
    if (!text || streaming) return
    setInput('')

    const userMsg: Msg = { role: 'user', content: text }
    const history = [...messages, userMsg]
    setMessages([...history, { role: 'assistant', content: '' }])
    setStreaming(true)

    const assistantIdx = history.length

    try {
      const BASE = (api.defaults.baseURL ?? 'http://localhost:8000').replace(/\/$/, '')
      const response = await fetch(`${BASE}/api/chat/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: history.map(m => ({ role: m.role, content: m.content })) }),
      })
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const reader  = response.body!.getReader()
      const decoder = new TextDecoder()
      let acc = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        acc += decoder.decode(value, { stream: true })
        setMessages(prev => {
          const u = [...prev]
          u[assistantIdx] = { role: 'assistant', content: acc }
          return u
        })
      }
    } catch {
      setMessages(prev => {
        const u = [...prev]
        u[assistantIdx] = { role: 'assistant', content: 'Erro de conexao. Verifique o backend.' }
        return u
      })
    } finally {
      setStreaming(false)
      inputRef.current?.focus()
    }
  }

  async function finalize() {
    setFinalizing(true)
    try {
      const res = await api.post('/api/chat/finalize', {
        messages: messages.map(m => ({ role: m.role, content: m.content })),
      })
      update({ topicProfile: res.data.profile })
      setFinalized(true)
    } catch {
      alert('Erro ao finalizar. Tente novamente.')
    } finally { setFinalizing(false) }
  }

  return (
    <Layout title="Definir Tema" subtitle="Chat para definir o perfil de especializacao do modelo">
      <div className="max-w-xl flex flex-col" style={{ height: 'calc(100vh - 120px)' }}>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto scrollbar-thin pb-3">
          {messages.map((msg, i) => <ChatMessage key={i} role={msg.role} content={msg.content} />)}
          {streaming && messages.at(-1)?.content === '' && (
            <div className="flex justify-start mb-2">
              <div className="w-6 h-6 rounded-sm bg-accent-500 flex items-center justify-center mr-2 mt-0.5">
                <span className="text-white font-bold text-[10px]">S</span>
              </div>
              <div className="bg-white border border-surface-200 rounded px-3 py-2 shadow-card">
                <motion.div className="flex gap-1 items-center h-4">
                  {[0,1,2].map(i => (
                    <motion.span key={i} className="w-1.5 h-1.5 bg-gray-400 rounded-sm"
                      animate={{ opacity: [0.3,1,0.3] }}
                      transition={{ repeat: Infinity, duration: 1, delay: i*0.2 }} />
                  ))}
                </motion.div>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="border-t border-surface-200 pt-3 space-y-2">
          <div className="flex justify-start mb-1">
            <button onClick={() => navigate('/model')} className="btn-secondary text-xs">
              <ArrowLeft size={13} /> Voltar
            </button>
          </div>
          {finalized ? (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              className="flex items-center justify-between bg-success-50 border border-green-200 rounded p-3">
              <div className="flex items-center gap-1.5 text-success-600 text-sm font-medium">
                <CheckCircle2 size={15} /> Tema definido com sucesso
              </div>
              <button onClick={() => navigate('/scraping/config')} className="btn-primary">
                Ir para Scraping <ArrowRight size={14} />
              </button>
            </motion.div>
          ) : (
            <>
              <div className="flex gap-2 items-end">
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
                  placeholder="Enter para enviar · Shift+Enter para nova linha"
                  rows={2}
                  disabled={streaming}
                  className="input resize-none flex-1 text-sm"
                />
                <button
                  onClick={send}
                  disabled={!input.trim() || streaming}
                  className="btn-primary h-[68px] w-10 p-0"
                >
                  <Send size={15} />
                </button>
              </div>
              {messages.length >= 7 && (
                <div className="flex justify-end">
                  <button onClick={finalize} disabled={finalizing || streaming} className="btn-secondary text-xs">
                    {finalizing ? 'Finalizando...' : 'Finalizar definicao de tema'}
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </Layout>
  )
}
