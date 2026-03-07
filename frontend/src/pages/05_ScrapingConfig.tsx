import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Globe, FileText, BookOpen, MessageSquare, ChevronRight } from 'lucide-react'
import { motion } from 'framer-motion'
import Layout from '../components/Layout'
import { useWizard } from '../context/WizardContext'
import api from '../lib/api'

const URL_LEVELS = [1000, 2000, 3000, 5000, 7500, 10000]

const SOURCE_TYPES = [
  { id: 'articles', label: 'Artigos', icon: FileText, desc: 'Blogs e sites de noticias' },
  { id: 'docs', label: 'Documentacao', icon: BookOpen, desc: 'Docs tecnicas e manuais' },
  { id: 'academic', label: 'Academico', icon: Globe, desc: 'Papers e publicacoes' },
  { id: 'forums', label: 'Forums', icon: MessageSquare, desc: 'Reddit, Stack Overflow, etc' },
]

function estimateTime(urlCount: number): string {
  const minutes = Math.ceil(urlCount / 60)
  if (minutes < 60) return `~${minutes} min`
  return `~${Math.ceil(minutes / 60)}h ${minutes % 60}min`
}

function estimateSize(urlCount: number): string {
  const mb = Math.round(urlCount * 0.8)
  return mb >= 1000 ? `~${(mb / 1000).toFixed(1)} GB` : `~${mb} MB`
}

export default function ScrapingConfig() {
  const { state, update, setCurrentStep } = useWizard()
  const navigate = useNavigate()

  const [urlLevel, setUrlLevel] = useState(1000)
  const [sources, setSources] = useState(['articles', 'docs'])
  const [saving, setSaving] = useState(false)

  useEffect(() => { setCurrentStep(5) }, [setCurrentStep])

  const profile = state.topicProfile as Record<string, unknown> | null
  const keywords = (profile?.keywords as string[]) ?? []
  const area = (profile?.area as string) ?? 'seu tema'

  function toggleSource(id: string) {
    setSources(prev =>
      prev.includes(id) ? prev.filter(s => s !== id) : [...prev, id]
    )
  }

  async function handleStart() {
    setSaving(true)
    const config = { url_count: urlLevel, sources, topic_profile: profile ?? {} }
    update({ scrapingConfig: { url_count: urlLevel, sources } })
    try {
      await api.post('/api/scraping/config', { url_count: urlLevel, topic_profile: profile ?? {} })
      await api.post('/api/scraping/start')
      navigate('/scraping/progress')
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } }
      alert(e.response?.data?.detail ?? 'Erro ao iniciar scraping')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Layout title="Configurar Scraping" subtitle="Defina o volume e fontes de dados a coletar">
      <div className="max-w-2xl space-y-6">

        {/* Topic summary */}
        {profile && (
          <div className="card bg-accent-500 text-white border-0">
            <p className="text-xs font-medium opacity-75 uppercase tracking-wide mb-1">
              Tema definido
            </p>
            <p className="font-semibold">{area}</p>
            {keywords.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-2">
                {keywords.slice(0, 6).map((kw: string) => (
                  <span key={kw} className="bg-white/20 text-white text-xs px-2 py-0.5 rounded-full">
                    {kw}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        {/* URL count slider */}
        <div className="card space-y-4">
          <div>
            <h3 className="text-base font-semibold text-gray-900">Volume de dados</h3>
            <p className="text-sm text-gray-500 mt-0.5">
              Mais URLs = modelo mais rico, mas leva mais tempo.
            </p>
          </div>

          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-2xl font-bold text-accent-500">
                {urlLevel.toLocaleString()}
              </span>
              <span className="text-sm text-gray-500">URLs</span>
            </div>

            <input
              type="range"
              min={0}
              max={URL_LEVELS.length - 1}
              value={URL_LEVELS.indexOf(urlLevel)}
              onChange={e => setUrlLevel(URL_LEVELS[parseInt(e.target.value)])}
              className="w-full accent-accent-500"
            />

            <div className="flex justify-between text-xs text-gray-400">
              {URL_LEVELS.map(n => (
                <span key={n}>{n >= 1000 ? `${n / 1000}k` : n}</span>
              ))}
            </div>
          </div>

          {/* Estimates */}
          <div className="grid grid-cols-2 gap-3">
            {[
              { label: 'Tempo estimado', value: estimateTime(urlLevel) },
              { label: 'Volume de dados', value: estimateSize(urlLevel) },
            ].map(item => (
              <div key={item.label} className="bg-surface-50 rounded-lg p-3 border border-surface-200">
                <p className="text-xs text-gray-500">{item.label}</p>
                <p className="text-lg font-semibold text-gray-900 mt-0.5">{item.value}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Source types */}
        <div className="card space-y-3">
          <h3 className="text-base font-semibold text-gray-900">Tipos de fonte</h3>
          <div className="grid grid-cols-2 gap-3">
            {SOURCE_TYPES.map(src => {
              const active = sources.includes(src.id)
              const Icon = src.icon
              return (
                <motion.button
                  key={src.id}
                  onClick={() => toggleSource(src.id)}
                  whileTap={{ scale: 0.97 }}
                  className={`flex items-start gap-3 p-3 rounded-lg border-2 text-left transition-colors
                    ${active
                      ? 'border-accent-500 bg-blue-50'
                      : 'border-surface-200 hover:border-accent-400'}`}
                >
                  <Icon size={18} className={active ? 'text-accent-500' : 'text-gray-400'} />
                  <div>
                    <p className={`text-sm font-medium ${active ? 'text-accent-500' : 'text-gray-700'}`}>
                      {src.label}
                    </p>
                    <p className="text-xs text-gray-500 mt-0.5">{src.desc}</p>
                  </div>
                </motion.button>
              )
            })}
          </div>
        </div>

        {/* Start button */}
        <div className="flex justify-end">
          <button
            onClick={handleStart}
            disabled={sources.length === 0 || saving}
            className="btn-primary px-8"
          >
            {saving ? 'Iniciando...' : `Iniciar Scraping de ${urlLevel.toLocaleString()} URLs`}
            <ChevronRight size={16} />
          </button>
        </div>

      </div>
    </Layout>
  )
}
