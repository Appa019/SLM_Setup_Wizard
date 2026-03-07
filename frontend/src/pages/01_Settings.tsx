import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Eye, EyeOff, CheckCircle2, XCircle, ArrowRight, Key, Mail } from 'lucide-react'
import { motion } from 'framer-motion'
import Layout from '../components/Layout'
import { useWizard } from '../context/WizardContext'
import api from '../lib/api'

export default function Settings() {
  const { update, setCurrentStep } = useWizard()
  const navigate = useNavigate()

  const [apiKey, setApiKey]         = useState('')
  const [googleEmail, setGoogleEmail] = useState('')
  const [showKey, setShowKey]       = useState(false)
  const [testing, setTesting]       = useState(false)
  const [result, setResult]         = useState<'idle'|'ok'|'error'>('idle')
  const [errorMsg, setErrorMsg]     = useState('')

  useEffect(() => {
    setCurrentStep(1)
    api.get('/api/settings/status').then(res => {
      if (res.data.openai_configured) setResult('ok')
      if (res.data.google_email)      setGoogleEmail(res.data.google_email)
    }).catch(() => {})
  }, [setCurrentStep])

  async function testKey() {
    if (!apiKey.trim()) return
    setTesting(true); setResult('idle'); setErrorMsg('')
    try {
      await api.post('/api/settings/openai-key', { api_key: apiKey.trim() })
      setResult('ok')
      update({ openaiKey: apiKey.trim() })
    } catch (err: unknown) {
      setResult('error')
      const e = err as { response?: { data?: { detail?: string } } }
      setErrorMsg(e.response?.data?.detail ?? 'Erro ao validar chave')
    } finally { setTesting(false) }
  }

  async function handleNext() {
    if (googleEmail.trim())
      await api.post('/api/settings/google-email', { email: googleEmail.trim() }).catch(() => {})
    navigate('/hardware')
  }

  const steps = [
    'Acesse platform.openai.com',
    'Faca login ou crie uma conta',
    'Va em "API Keys" no menu lateral',
    'Clique em "Create new secret key"',
    'Copie e cole a chave abaixo',
  ]

  return (
    <Layout title="Configuracoes" subtitle="Credenciais necessarias para o wizard">
      <div className="max-w-xl space-y-4">

        {/* OpenAI Key */}
        <div className="card space-y-4">
          <div className="flex items-center gap-2 border-b border-surface-200 pb-3">
            <Key size={15} className="text-accent-500" />
            <h2 className="font-semibold text-gray-900 text-sm">OpenAI API Key</h2>
          </div>

          <div className="bg-surface-50 border border-surface-200 rounded p-3 space-y-1.5">
            <p className="section-title mb-2">Como obter</p>
            {steps.map((s, i) => (
              <div key={i} className="flex gap-2 text-xs text-gray-600">
                <span className="w-4 h-4 rounded-sm bg-accent-500 text-white flex items-center justify-center text-[10px] font-bold flex-shrink-0 mt-0.5">
                  {i + 1}
                </span>
                {s}
              </div>
            ))}
            <p className="text-[11px] text-warning-600 mt-2 border-t border-surface-200 pt-2">
              Necessario ter creditos no plano pay-as-you-go
            </p>
          </div>

          <div className="flex gap-2">
            <div className="relative flex-1">
              <input
                type={showKey ? 'text' : 'password'}
                value={apiKey}
                onChange={e => { setApiKey(e.target.value); setResult('idle') }}
                placeholder="sk-proj-..."
                className="input font-mono pr-9"
              />
              <button
                onClick={() => setShowKey(v => !v)}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                {showKey ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            </div>
            <button
              onClick={testKey}
              disabled={!apiKey.trim() || testing}
              className="btn-primary whitespace-nowrap"
            >
              {testing ? 'Testando...' : 'Testar'}
            </button>
          </div>

          {result === 'ok' && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              className="flex items-center gap-1.5 text-success-600 text-xs font-medium">
              <CheckCircle2 size={14} /> Chave valida e salva
            </motion.div>
          )}
          {result === 'error' && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              className="flex items-center gap-1.5 text-danger-600 text-xs">
              <XCircle size={14} /> {errorMsg}
            </motion.div>
          )}
        </div>

        {/* Google Account */}
        <div className="card space-y-4">
          <div className="flex items-center gap-2 border-b border-surface-200 pb-3">
            <Mail size={15} className="text-accent-500" />
            <h2 className="font-semibold text-gray-900 text-sm">Conta Google</h2>
          </div>

          <div className="bg-accent-50 border border-accent-100 rounded p-3 text-xs text-accent-700 space-y-1">
            <p className="font-medium text-accent-600">Sem configuracao necessaria</p>
            <p>
              Na etapa de treinamento, abriremos o Google Colab no seu browser automaticamente.
              Voce so precisa estar logado na conta Google.
            </p>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1.5">
              Email Google (referencia)
            </label>
            <input
              type="email"
              value={googleEmail}
              onChange={e => setGoogleEmail(e.target.value)}
              placeholder="seu@gmail.com"
              className="input max-w-xs"
            />
          </div>
        </div>

        <div className="flex justify-end">
          <button
            onClick={handleNext}
            disabled={result !== 'ok'}
            className="btn-primary"
          >
            Proximo: Hardware <ArrowRight size={14} />
          </button>
        </div>

      </div>
    </Layout>
  )
}
