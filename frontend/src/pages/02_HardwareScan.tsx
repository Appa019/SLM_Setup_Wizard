import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Cpu, MemoryStick, HardDrive, Monitor, ChevronRight } from 'lucide-react'
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

const TIER_COLOR: Record<string, string> = {
  high: 'badge-green',
  mid: 'badge-yellow',
  low: 'badge-yellow',
  minimal: 'badge-red',
}

export default function HardwareScan() {
  const { update, setCurrentStep } = useWizard()
  const navigate = useNavigate()
  const [data, setData] = useState<HardwareData | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    setCurrentStep(2)
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
      .catch(() => setError('Erro ao escanear hardware'))
  }, [setCurrentStep, update])

  return (
    <Layout title="Scan de Hardware" subtitle="Detectando os componentes do seu sistema">
      <div className="max-w-2xl space-y-6">

        {!data && !error && <Loader message="Escaneando hardware..." />}

        {error && (
          <div className="card border-red-200 bg-red-50 text-red-700 text-sm">{error}</div>
        )}

        {data && (
          <>
            {/* Capacity badge */}
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="card flex items-center justify-between"
            >
              <div>
                <p className="text-sm text-gray-500">Capacidade detectada</p>
                <p className="text-lg font-semibold text-gray-900 mt-0.5">
                  Modelos de ate <span className="text-accent-500">{data.capacity.max_params}</span> parametros
                </p>
              </div>
              <span className={TIER_COLOR[data.capacity.tier] ?? 'badge-yellow'}>
                {data.capacity.label}
              </span>
            </motion.div>

            {/* Hardware cards */}
            <div className="grid grid-cols-2 gap-4">
              {[
                {
                  icon: <Cpu size={18} className="text-accent-500" />,
                  label: 'Processador',
                  value: data.cpu.model || 'Desconhecido',
                  detail: `${data.cpu.cores} cores · ${data.cpu.freq_ghz} GHz`,
                },
                {
                  icon: <MemoryStick size={18} className="text-accent-500" />,
                  label: 'Memoria RAM',
                  value: `${data.ram.total_gb} GB`,
                  detail: `${data.ram.available_gb} GB disponivel`,
                },
                {
                  icon: <Monitor size={18} className="text-accent-500" />,
                  label: 'GPU',
                  value: data.gpu?.model ?? 'Nao detectada',
                  detail: data.gpu ? `${data.gpu.vram_gb} GB VRAM` : 'Sera usado CPU para inferencia',
                },
                {
                  icon: <HardDrive size={18} className="text-accent-500" />,
                  label: 'Disco',
                  value: `${data.disk.free_gb} GB livres`,
                  detail: data.os,
                },
              ].map((item, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.08 }}
                  className="card space-y-2"
                >
                  <div className="flex items-center gap-2 text-sm font-medium text-gray-700">
                    {item.icon}
                    {item.label}
                  </div>
                  <p className="text-sm font-semibold text-gray-900 truncate">{item.value}</p>
                  <p className="text-xs text-gray-500">{item.detail}</p>
                </motion.div>
              ))}
            </div>

            {/* Next */}
            <div className="flex justify-end">
              <button onClick={() => navigate('/model')} className="btn-primary px-8">
                Proximo: Selecionar Modelo <ChevronRight size={16} />
              </button>
            </div>
          </>
        )}

      </div>
    </Layout>
  )
}
