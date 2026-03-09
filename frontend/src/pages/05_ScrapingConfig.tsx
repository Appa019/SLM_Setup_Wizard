import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Globe, FileText, BookOpen, MessageSquare, ArrowRight, ArrowLeft, Tag, Sparkles, X, Plus } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import Layout from '../components/Layout'
import Loader from '../components/Loader'
import { useWizard } from '../context/WizardContext'
import api from '../lib/api'

const SOURCES = [
  { id: 'articles', label: 'Artigos',       icon: FileText,      desc: 'Blogs e noticias' },
  { id: 'docs',     label: 'Documentacao',  icon: BookOpen,      desc: 'Docs e manuais' },
  { id: 'academic', label: 'Academico',     icon: Globe,         desc: 'Papers e publicacoes' },
  { id: 'forums',   label: 'Forums',        icon: MessageSquare, desc: 'Reddit, Stack Overflow' },
]

export default function ScrapingConfig() {
  const { state, update, setCurrentStep } = useWizard()
  const navigate = useNavigate()

  const [queryCount, setQueryCount] = useState(50)
  const [sources, setSources]       = useState(['articles', 'docs'])
  const [queries, setQueries]       = useState<string[]>([])
  const [loadingQ, setLoadingQ]     = useState(false)
  const [queryInput, setQueryInput] = useState('')
  const [saving, setSaving]         = useState(false)

  useEffect(() => { setCurrentStep(5) }, [setCurrentStep])

  const profile  = state.topicProfile as Record<string, unknown> | null
  const keywords = (profile?.keywords as string[]) ?? []
  const area     = (profile?.area as string) ?? 'Tema nao definido'

  function toggleSource(id: string) {
    setSources(prev => prev.includes(id) ? prev.filter(s => s !== id) : [...prev, id])
  }

  function removeQuery(idx: number) {
    setQueries(prev => prev.filter((_, i) => i !== idx))
  }

  function addQuery() {
    const q = queryInput.trim()
    if (!q || queries.includes(q)) return
    setQueries(prev => [...prev, q])
    setQueryInput('')
  }

  async function generateQueries() {
    if (!profile || loadingQ) return
    setLoadingQ(true)
    try {
      const res = await api.post('/api/scraping/generate-queries', {
        topic_profile: profile,
        count: queryCount,
      })
      setQueries(res.data.queries)
    } catch { /* silencioso */ } finally {
      setLoadingQ(false)
    }
  }

  async function start() {
    if (saving || queries.length === 0) return
    setSaving(true)
    update({ scrapingConfig: { url_count: queryCount * 20, sources } })
    try {
      await api.post('/api/scraping/config', {
        query_count: queryCount,
        topic_profile: profile ?? {},
        custom_queries: queries,
      })
      await api.post('/api/scraping/start')
      navigate('/scraping/progress')
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } }
      alert(e.response?.data?.detail ?? 'Erro ao iniciar scraping')
    } finally { setSaving(false) }
  }

  const canStart = sources.length > 0 && queries.length > 0 && !saving

  return (
    <Layout title="Configurar Scraping" subtitle="Defina as queries de pesquisa e fontes de dados">
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

        {/* Query count + generate */}
        <div className="card space-y-4">
          <h3 className="font-display text-[11px] font-bold text-gray-900 uppercase tracking-[0.08em] border-b border-surface-200 pb-2">
            Queries de pesquisa
          </h3>

          <div className="space-y-2">
            <div className="flex justify-between items-baseline">
              <span className="text-2xl font-bold text-accent-500 font-mono">{queryCount}</span>
              <span className="text-xs text-gray-400">queries</span>
            </div>
            <input
              type="range" min={10} max={150} step={5}
              value={queryCount}
              onChange={e => { setQueryCount(parseInt(e.target.value)); setQueries([]) }}
              className="w-full accent-accent-500 h-1.5"
            />
            <div className="flex justify-between text-[10px] text-gray-400 font-mono">
              <span>10</span><span>50</span><span>100</span><span>150</span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2">
            {[
              { label: 'URLs estimadas',  value: `~${(queryCount * 20).toLocaleString()}` },
              { label: 'Tempo estimado',  value: `~${Math.ceil(queryCount * 20 / 60)} min` },
            ].map(item => (
              <div key={item.label} className="bg-surface-50 border border-surface-200 p-3">
                <p className="text-[11px] text-gray-500">{item.label}</p>
                <p className="font-semibold text-gray-900 mt-0.5 font-mono">{item.value}</p>
              </div>
            ))}
          </div>

          <button
            onClick={generateQueries}
            disabled={!profile || loadingQ}
            className="btn-primary w-full justify-center"
          >
            <Sparkles size={13} />
            {loadingQ ? 'Gerando...' : queries.length > 0 ? 'Regenerar queries' : 'Gerar com IA'}
          </button>

          {loadingQ && <Loader message={`Gerando ${queryCount} queries com GPT-4o-mini...`} />}
        </div>

        {/* Query list */}
        <AnimatePresence>
          {queries.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
              className="card space-y-3"
            >
              <div className="flex items-center justify-between border-b border-surface-200 pb-2">
                <h3 className="font-display text-[11px] font-bold text-gray-900 uppercase tracking-[0.08em]">
                  Queries selecionadas
                </h3>
                <span className="badge-blue">{queries.length} queries</span>
              </div>

              <div className="flex flex-wrap gap-1.5 max-h-48 overflow-y-auto pr-1">
                {queries.map((q, i) => (
                  <motion.span
                    key={i}
                    initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }}
                    className="flex items-center gap-1 badge-blue text-[10px] pr-1"
                  >
                    {q}
                    <button
                      onClick={() => removeQuery(i)}
                      className="ml-0.5 hover:text-red-500 transition-colors"
                    >
                      <X size={10} />
                    </button>
                  </motion.span>
                ))}
              </div>

              {/* Add custom query */}
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="Adicionar query manualmente..."
                  value={queryInput}
                  onChange={e => setQueryInput(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && addQuery()}
                  className="input flex-1 text-xs"
                />
                <button onClick={addQuery} className="btn-secondary px-2" title="Adicionar">
                  <Plus size={13} />
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Sources */}
        <div className="card space-y-3">
          <h3 className="font-display text-[11px] font-bold text-gray-900 uppercase tracking-[0.08em] border-b border-surface-200 pb-2">
            Tipos de fonte
          </h3>
          <div className="grid grid-cols-2 gap-2">
            {SOURCES.map(src => {
              const on = sources.includes(src.id)
              const Icon = src.icon
              return (
                <motion.button
                  key={src.id}
                  onClick={() => toggleSource(src.id)}
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

        <div className="flex flex-col gap-2">
          {queries.length === 0 && (
            <p className="text-[11px] text-gray-400 text-center">
              Gere as queries com IA antes de iniciar o scraping
            </p>
          )}
          <div className="flex justify-between items-center">
            <button onClick={() => navigate('/topic')} className="btn-secondary">
              <ArrowLeft size={14} /> Voltar
            </button>
            <button onClick={start} disabled={!canStart} className="btn-primary">
              {saving ? 'Iniciando...' : `Iniciar scraping — ${queries.length} queries`}
              <ArrowRight size={14} />
            </button>
          </div>
        </div>

      </div>
    </Layout>
  )
}
