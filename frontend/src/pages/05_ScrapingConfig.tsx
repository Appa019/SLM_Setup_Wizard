import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Globe, FileText, BookOpen, MessageSquare, ArrowRight, ArrowLeft, Tag } from 'lucide-react'
import { motion } from 'framer-motion'
import Layout from '../components/Layout'
import { useWizard } from '../context/WizardContext'
import api from '../lib/api'

const URL_LEVELS = [1000, 2000, 3000, 5000, 7500, 10000]

const SOURCES = [
  { id: 'articles', label: 'Artigos',       icon: FileText,      desc: 'Blogs e noticias' },
  { id: 'docs',     label: 'Documentacao',  icon: BookOpen,      desc: 'Docs e manuais' },
  { id: 'academic', label: 'Academico',     icon: Globe,         desc: 'Papers e publicacoes' },
  { id: 'forums',   label: 'Forums',        icon: MessageSquare, desc: 'Reddit, Stack Overflow' },
]

const estTime = (n: number) => {
  const m = Math.ceil(n / 60)
  return m < 60 ? `${m}min` : `${Math.ceil(m/60)}h${m%60?` ${m%60}min`:''}`
}
const estSize = (n: number) => {
  const mb = Math.round(n * 0.8)
  return mb >= 1000 ? `${(mb/1000).toFixed(1)} GB` : `${mb} MB`
}

export default function ScrapingConfig() {
  const { state, update, setCurrentStep } = useWizard()
  const navigate = useNavigate()

  const [urlLevel, setUrlLevel] = useState(1000)
  const [sources, setSources]   = useState(['articles', 'docs'])
  const [saving, setSaving]     = useState(false)

  useEffect(() => { setCurrentStep(5) }, [setCurrentStep])

  const profile  = state.topicProfile as Record<string, unknown> | null
  const keywords = (profile?.keywords as string[]) ?? []
  const area     = (profile?.area as string) ?? 'Tema nao definido'

  function toggle(id: string) {
    setSources(prev => prev.includes(id) ? prev.filter(s => s !== id) : [...prev, id])
  }

  async function start() {
    setSaving(true)
    update({ scrapingConfig: { url_count: urlLevel, sources } })
    try {
      await api.post('/api/scraping/config', { url_count: urlLevel, topic_profile: profile ?? {} })
      await api.post('/api/scraping/start')
      navigate('/scraping/progress')
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } }
      alert(e.response?.data?.detail ?? 'Erro ao iniciar scraping')
    } finally { setSaving(false) }
  }

  return (
    <Layout title="Configurar Scraping" subtitle="Volume e fontes de dados a coletar">
      <div className="max-w-xl space-y-4">

        {/* Topic badge */}
        {profile && (
          <div className="card-sm flex flex-col gap-2">
            <div className="flex items-center gap-1.5 section-title mb-0">
              <Tag size={11} /> Tema definido
            </div>
            <p className="font-semibold text-gray-900 text-sm">{area}</p>
            {keywords.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {keywords.slice(0, 8).map(kw => (
                  <span key={kw} className="badge-blue text-[10px]">{kw}</span>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Volume */}
        <div className="card space-y-4">
          <h3 className="text-sm font-semibold text-gray-900 border-b border-surface-200 pb-2">
            Volume de dados
          </h3>

          <div className="space-y-2">
            <div className="flex justify-between items-baseline">
              <span className="text-2xl font-bold text-accent-500 font-mono">
                {urlLevel.toLocaleString()}
              </span>
              <span className="text-xs text-gray-400">URLs</span>
            </div>
            <input
              type="range" min={0} max={URL_LEVELS.length - 1}
              value={URL_LEVELS.indexOf(urlLevel)}
              onChange={e => setUrlLevel(URL_LEVELS[parseInt(e.target.value)])}
              className="w-full accent-accent-500 h-1.5"
            />
            <div className="flex justify-between text-[10px] text-gray-400 font-mono">
              {URL_LEVELS.map(n => <span key={n}>{n >= 1000 ? `${n/1000}k` : n}</span>)}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2">
            {[
              { label: 'Tempo estimado', value: estTime(urlLevel) },
              { label: 'Volume de dados', value: estSize(urlLevel) },
            ].map(item => (
              <div key={item.label} className="bg-surface-50 border border-surface-200 rounded p-3">
                <p className="text-[11px] text-gray-500">{item.label}</p>
                <p className="font-semibold text-gray-900 mt-0.5">{item.value}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Sources */}
        <div className="card space-y-3">
          <h3 className="text-sm font-semibold text-gray-900 border-b border-surface-200 pb-2">
            Tipos de fonte
          </h3>
          <div className="grid grid-cols-2 gap-2">
            {SOURCES.map(src => {
              const on = sources.includes(src.id)
              const Icon = src.icon
              return (
                <motion.button
                  key={src.id}
                  onClick={() => toggle(src.id)}
                  whileTap={{ scale: 0.98 }}
                  className={`flex items-center gap-2.5 p-3 rounded border-2 text-left transition-colors
                    ${on ? 'border-accent-500 bg-accent-50' : 'border-surface-200 hover:border-surface-300'}`}
                >
                  <Icon size={15} className={on ? 'text-accent-500' : 'text-gray-400'} />
                  <div>
                    <p className={`text-xs font-semibold ${on ? 'text-accent-600' : 'text-gray-700'}`}>
                      {src.label}
                    </p>
                    <p className="text-[10px] text-gray-400">{src.desc}</p>
                  </div>
                </motion.button>
              )
            })}
          </div>
        </div>

        <div className="flex justify-between items-center">
          <button onClick={() => navigate('/topic')} className="btn-secondary">
            <ArrowLeft size={14} /> Voltar
          </button>
          <button onClick={start} disabled={sources.length === 0 || saving} className="btn-primary">
            {saving ? 'Iniciando...' : `Iniciar scraping — ${urlLevel.toLocaleString()} URLs`}
            <ArrowRight size={14} />
          </button>
        </div>
      </div>
    </Layout>
  )
}
