import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Eye, EyeOff, CheckCircle, XCircle, ExternalLink } from 'lucide-react'
import { motion } from 'framer-motion'
import Layout from '../components/Layout'
import { useWizard } from '../context/WizardContext'
import api from '../lib/api'

export default function Settings() {
  const { update, setCurrentStep } = useWizard()
  const navigate = useNavigate()

  const [apiKey, setApiKey] = useState('')
  const [googleEmail, setGoogleEmail] = useState('')
  const [showKey, setShowKey] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<'idle' | 'ok' | 'error'>('idle')
  const [errorMsg, setErrorMsg] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    setCurrentStep(1)
    api.get('/api/settings/status').then(res => {
      if (res.data.openai_configured) setTestResult('ok')
      if (res.data.google_email) setGoogleEmail(res.data.google_email)
    }).catch(() => {})
  }, [setCurrentStep])

  async function handleTestKey() {
    if (!apiKey.trim()) return
    setTesting(true)
    setTestResult('idle')
    setErrorMsg('')
    try {
      await api.post('/api/settings/openai-key', { api_key: apiKey.trim() })
      setTestResult('ok')
      update({ openaiKey: apiKey.trim() })
    } catch (err: unknown) {
      setTestResult('error')
      if (err && typeof err === 'object' && 'response' in err) {
        const e = err as { response?: { data?: { detail?: string } } }
        setErrorMsg(e.response?.data?.detail ?? 'Erro ao validar chave')
      } else {
        setErrorMsg('Erro ao conectar com o backend')
      }
    } finally {
      setTesting(false)
    }
  }

  async function handleSaveEmail() {
    if (!googleEmail.trim()) return
    await api.post('/api/settings/google-email', { email: googleEmail.trim() })
  }

  async function handleNext() {
    if (testResult !== 'ok') return
    setSaving(true)
    await handleSaveEmail()
    setSaving(false)
    navigate('/hardware')
  }

  return (
    <Layout
      title="Configuracoes"
      subtitle="Configure suas credenciais para comecar o wizard"
    >
      <div className="max-w-2xl space-y-6">

        {/* OpenAI API Key */}
        <div className="card space-y-4">
          <div>
            <h3 className="text-base font-semibold text-gray-900">OpenAI API Key</h3>
            <p className="text-sm text-gray-500 mt-0.5">
              Usada para recomendacoes, chatbot de tema e pre-processamento dos dados.
            </p>
          </div>

          {/* Instructions */}
          <div className="bg-surface-50 rounded-lg border border-surface-200 p-4 space-y-1.5 text-sm text-gray-600">
            <p className="font-medium text-gray-700 mb-2">Como obter sua chave:</p>
            {[
              'Acesse platform.openai.com',
              'Faca login ou crie uma conta',
              'Va em "API Keys" no menu lateral',
              'Clique em "Create new secret key"',
              'Copie a chave (comeca com sk-...)',
              'Cole no campo abaixo',
            ].map((step, i) => (
              <div key={i} className="flex items-start gap-2">
                <span className="flex-shrink-0 w-5 h-5 rounded-full bg-accent-500 text-white text-xs flex items-center justify-center mt-0.5">
                  {i + 1}
                </span>
                <span>{step}</span>
              </div>
            ))}
            <p className="text-xs text-amber-600 mt-2 flex items-center gap-1">
              Necessario ter creditos na conta (plano pay-as-you-go)
            </p>
          </div>

          {/* Input */}
          <div className="flex gap-2">
            <div className="relative flex-1">
              <input
                type={showKey ? 'text' : 'password'}
                value={apiKey}
                onChange={e => { setApiKey(e.target.value); setTestResult('idle') }}
                placeholder="sk-..."
                className="input pr-10 font-mono text-sm"
              />
              <button
                onClick={() => setShowKey(v => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
            <button
              onClick={handleTestKey}
              disabled={!apiKey.trim() || testing}
              className="btn-primary min-w-[120px]"
            >
              {testing ? 'Testando...' : 'Testar Conexao'}
            </button>
          </div>

          {/* Result feedback */}
          {testResult === 'ok' && (
            <motion.div
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-center gap-2 text-green-600 text-sm"
            >
              <CheckCircle size={16} />
              Chave valida e salva com sucesso
            </motion.div>
          )}
          {testResult === 'error' && (
            <motion.div
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-center gap-2 text-red-600 text-sm"
            >
              <XCircle size={16} />
              {errorMsg}
            </motion.div>
          )}
        </div>

        {/* Google Account */}
        <div className="card space-y-4">
          <div>
            <h3 className="text-base font-semibold text-gray-900">Conta Google</h3>
            <p className="text-sm text-gray-500 mt-0.5">
              Necessaria para o treinamento no Google Colab.
            </p>
          </div>

          <div className="bg-blue-50 border border-blue-100 rounded-lg p-4 text-sm text-blue-800 space-y-1">
            <p className="font-medium">Como funciona:</p>
            <p>
              Quando chegar a etapa de treinamento, abriremos o Google Colab automaticamente
              no seu navegador. Voce so precisa estar logado na sua conta Google — nenhuma
              configuracao adicional e necessaria.
            </p>
            <a
              href="https://colab.research.google.com"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-blue-600 hover:underline mt-1"
            >
              Abrir Google Colab <ExternalLink size={13} />
            </a>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Email Google (para referencia)
            </label>
            <input
              type="email"
              value={googleEmail}
              onChange={e => setGoogleEmail(e.target.value)}
              placeholder="seu@gmail.com"
              className="input max-w-sm"
            />
          </div>
        </div>

        {/* Next */}
        <div className="flex justify-end">
          <button
            onClick={handleNext}
            disabled={testResult !== 'ok' || saving}
            className="btn-primary px-8"
          >
            {saving ? 'Salvando...' : 'Proximo: Scan de Hardware'}
          </button>
        </div>

      </div>
    </Layout>
  )
}
