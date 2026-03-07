import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Send, ChevronRight, CheckCircle } from 'lucide-react'
import { motion } from 'framer-motion'
import Layout from '../components/Layout'
import ChatMessage from '../components/ChatMessage'
import { useWizard } from '../context/WizardContext'
import api from '../lib/api'

interface Msg { role: 'user' | 'assistant'; content: string }

const WELCOME: Msg = {
  role: 'assistant',
  content:
    'Ola! Vou te ajudar a definir o tema do seu modelo especializado.\n\n' +
    'Para comecar: qual e a area de conhecimento que voce quer que o modelo domine? ' +
    'Pode ser algo especifico como "direito trabalhista brasileiro", "culinaria vegana" ou "programacao em Rust".',
}

export default function TopicChat() {
  const { update, setCurrentStep } = useWizard()
  const navigate = useNavigate()

  const [messages, setMessages] = useState<Msg[]>([WELCOME])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [finalizing, setFinalizing] = useState(false)
  const [finalized, setFinalized] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => { setCurrentStep(4) }, [setCurrentStep])
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function sendMessage() {
    const text = input.trim()
    if (!text || streaming) return
    setInput('')

    const userMsg: Msg = { role: 'user', content: text }
    const history = [...messages, userMsg]
    setMessages(history)
    setStreaming(true)

    // Add empty assistant bubble to fill
    const assistantIdx = history.length
    setMessages(prev => [...prev, { role: 'assistant', content: '' }])

    try {
      const response = await fetch('http://localhost:8000/api/chat/message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: history.map(m => ({ role: m.role, content: m.content })),
        }),
      })

      if (!response.body) throw new Error('No stream body')
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let accumulated = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        accumulated += decoder.decode(value, { stream: true })
        setMessages(prev => {
          const updated = [...prev]
          updated[assistantIdx] = { role: 'assistant', content: accumulated }
          return updated
        })
      }
    } catch {
      setMessages(prev => {
        const updated = [...prev]
        updated[assistantIdx] = { role: 'assistant', content: 'Erro ao conectar. Verifique o backend.' }
        return updated
      })
    } finally {
      setStreaming(false)
      inputRef.current?.focus()
    }
  }

  async function handleFinalize() {
    setFinalizing(true)
    try {
      const res = await api.post('/api/chat/finalize', {
        messages: messages.map(m => ({ role: m.role, content: m.content })),
      })
      update({ topicProfile: res.data.profile })
      setFinalized(true)
    } catch {
      alert('Erro ao finalizar. Tente novamente.')
    } finally {
      setFinalizing(false)
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <Layout
      title="Definir Tema"
      subtitle="Converse com o assistente para definir o perfil do seu modelo"
    >
      <div className="max-w-2xl flex flex-col" style={{ height: 'calc(100vh - 140px)' }}>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto space-y-1 pb-4 scrollbar-thin">
          {messages.map((msg, i) => (
            <ChatMessage key={i} role={msg.role} content={msg.content} />
          ))}
          {streaming && messages[messages.length - 1]?.content === '' && (
            <div className="flex justify-start mb-3">
              <div className="bg-white border border-surface-200 rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm">
                <motion.div className="flex gap-1">
                  {[0, 1, 2].map(i => (
                    <motion.span
                      key={i}
                      className="w-1.5 h-1.5 bg-gray-400 rounded-full"
                      animate={{ opacity: [0.3, 1, 0.3] }}
                      transition={{ repeat: Infinity, duration: 1, delay: i * 0.2 }}
                    />
                  ))}
                </motion.div>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input area */}
        <div className="border-t border-surface-200 pt-4 space-y-3">
          {finalized ? (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-center justify-between bg-green-50 border border-green-200 rounded-xl p-4"
            >
              <div className="flex items-center gap-2 text-green-700 text-sm font-medium">
                <CheckCircle size={18} />
                Perfil de tema definido com sucesso!
              </div>
              <button onClick={() => navigate('/scraping/config')} className="btn-primary">
                Proximo: Scraping <ChevronRight size={16} />
              </button>
            </motion.div>
          ) : (
            <>
              <div className="flex gap-2 items-end">
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Digite sua mensagem... (Enter para enviar, Shift+Enter para nova linha)"
                  rows={2}
                  disabled={streaming}
                  className="input resize-none flex-1 text-sm leading-relaxed"
                />
                <button
                  onClick={sendMessage}
                  disabled={!input.trim() || streaming}
                  className="btn-primary h-10 w-10 p-0 justify-center flex-shrink-0"
                >
                  <Send size={16} />
                </button>
              </div>

              {messages.length >= 7 && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex justify-end"
                >
                  <button
                    onClick={handleFinalize}
                    disabled={finalizing || streaming}
                    className="btn-secondary text-sm"
                  >
                    {finalizing ? 'Finalizando...' : 'Finalizar Definicao de Tema'}
                  </button>
                </motion.div>
              )}
            </>
          )}
        </div>

      </div>
    </Layout>
  )
}
