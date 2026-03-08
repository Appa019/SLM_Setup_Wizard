import type { ReactNode } from 'react'
import { motion } from 'framer-motion'
import Stepper from './Stepper'
import CostPanel from './CostPanel'

interface LayoutProps {
  children: ReactNode
  title: string
  subtitle?: string
  actions?: ReactNode
}

export default function Layout({ children, title, subtitle, actions }: LayoutProps) {
  return (
    <div className="min-h-screen flex bg-surface-50">
      {/* Sidebar */}
      <aside className="w-56 flex-shrink-0 bg-white border-r border-surface-200 flex flex-col">
        {/* Logo */}
        <div className="h-12 flex items-center px-4 border-b border-surface-200 gap-2.5">
          <img src="/logo.png" className="h-7 w-7" alt="SLM" />
          <div>
            <p className="font-display text-sm text-gray-900 tracking-wide leading-tight">SLM Local</p>
            <p className="text-[10px] text-gray-400">Fine-tuning wizard</p>
          </div>
        </div>
        <div className="h-[1px] bg-accent-500/20 mx-4" />
        <div className="flex-1 overflow-y-auto scrollbar-thin py-2 bg-dot-grid-light bg-dot-16">
          <Stepper />
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 flex flex-col min-h-screen overflow-hidden">
        {/* Topbar */}
        <header className="h-12 border-b border-surface-200 bg-white flex items-center justify-between px-6 flex-shrink-0">
          <div>
            <motion.h1
              key={title}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="font-display text-[11px] font-bold text-gray-900 uppercase tracking-[0.08em]"
            >
              {title}
            </motion.h1>
            {subtitle && (
              <p className="text-[11px] text-gray-400 leading-tight mt-0.5">{subtitle}</p>
            )}
          </div>
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </header>

        {/* Content */}
        <motion.div
          key={title}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.18, ease: 'easeOut' }}
          className="flex-1 overflow-y-auto p-6 scrollbar-thin"
        >
          {children}
        </motion.div>
      </main>
      <CostPanel />
    </div>
  )
}
