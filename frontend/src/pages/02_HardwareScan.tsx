import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Cpu, MemoryStick, HardDrive, Monitor, ArrowRight, ArrowLeft, RefreshCw } from 'lucide-react'
import { motion } from 'framer-motion'
import Layout from '../components/Layout'
import Loader from '../components/Loader'
import { useWizard } from '../context/WizardContext'
import api from '../lib/api'

interface HardwareData {
  cpu: { model: string; cores: number; freq_ghz: number }
  ram: { total_gb: number; available_gb: number }
  gpu: { model: string; vram_gb: number } | null
  disk: { free_gb: number }
  os: string
  capacity: { max_params: string; tier: string; label: string }
}

const TIER_BADGE: Record<string, string> = {
  high:    'badge-green',
  mid:     'badge-yellow',
  low:     'badge-yellow',
  minimal: 'badge-red',
}

const HW_ITEMS = (d: HardwareData) => [
  { icon: Cpu,         label: 'Processador', value: d.cpu.model || 'Desconhecido',  sub: `${d.cpu.cores} cores · ${d.cpu.freq_ghz} GHz` },
  { icon: MemoryStick, label: 'Memoria RAM', value: `${d.ram.total_gb} GB`,         sub: `${d.ram.available_gb} GB disponivel` },
  { icon: Monitor,     label: 'GPU',         value: d.gpu?.model ?? 'Nao detectada', sub: d.gpu ? `${d.gpu.vram_gb} GB VRAM` : 'Inferencia via CPU' },
  { icon: HardDrive,   label: 'Disco',       value: `${d.disk.free_gb} GB livres`,  sub: d.os },
]

export default function HardwareScan() {
  const { update, setCurrentStep } = useWizard()
  const navigate = useNavigate()
  const [data, setData]     = useState<HardwareData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]   = useState('')

  const fetchHardware = () => {
    setLoading(true); setError('')
    api.get<HardwareData>('/api/hardware/scan')
      .then(res => {
        setData(res.data)
        update({
          hardware: {
            cpu: res.data.cpu.model,
            ram_gb: res.data.ram.total_gb,
            gpu: res.data.gpu?.model,
            vram_gb: res.data.gpu?.vram_gb,
            disk_free_gb: res.data.disk.free_gb,
            os: res.data.os,
          }
        })
      })
      .catch((err) => {
        if (!err.response) {
          setError('Backend não está rodando. Inicie o servidor e tente novamente.')
        } else {
          setError(`Erro ao escanear hardware: ${err.response?.data?.detail || 'tente novamente'}`)
        }
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => { setCurrentStep(2); fetchHardware() }, [setCurrentStep])

  return (
    <Layout
      title="Scan de Hardware"
      subtitle="Detectando os componentes do sistema"
      actions={
        data && (
          <button onClick={fetchHardware} className="btn-ghost text-xs">
            <RefreshCw size={13} /> Reatualizar
          </button>
        )
      }
    >
      <div className="max-w-xl space-y-4">
        {loading && <Loader message="Escaneando hardware..." />}

        {error && (
          <div className="card border-red-200 bg-danger-50 text-danger-600 text-xs p-3">
            {error}
          </div>
        )}

        {data && (
          <>
            {/* Capacity summary */}
            <motion.div
              initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
              className="card flex items-center justify-between"
            >
              <div>
                <p className="section-title mb-0.5">Capacidade detectada</p>
                <p className="text-base font-semibold text-gray-900">
                  Modelos ate <span className="text-accent-500">{data.capacity.max_params}</span> parametros
                </p>
              </div>
              <span className={TIER_BADGE[data.capacity.tier] ?? 'badge-yellow'}>
                {data.capacity.label}
              </span>
            </motion.div>

            {/* Hardware grid */}
            <div className="grid grid-cols-2 gap-3">
              {HW_ITEMS(data).map((item, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.06 }}
                  className="card-sm space-y-2 border-l-2 border-l-accent-500"
                >
                  <div className="flex items-center gap-1.5 text-gray-500 text-xs font-medium">
                    <item.icon size={13} className="text-accent-500" />
                    {item.label}
                  </div>
                  <p className="text-sm font-semibold text-gray-900 truncate font-mono">{item.value}</p>
                  <p className="text-[11px] text-gray-400 leading-tight">{item.sub}</p>
                </motion.div>
              ))}
            </div>

            <div className="flex justify-between items-center">
              <button onClick={() => navigate('/settings')} className="btn-secondary">
                <ArrowLeft size={14} /> Voltar
              </button>
              <button onClick={() => navigate('/model')} className="btn-primary">
                Selecionar Modelo <ArrowRight size={14} />
              </button>
            </div>
          </>
        )}
      </div>
    </Layout>
  )
}
