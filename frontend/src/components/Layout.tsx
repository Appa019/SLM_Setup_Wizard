import type { ReactNode } from 'react'
import { motion } from 'framer-motion'
import Stepper from './Stepper'

interface LayoutProps {
  children: ReactNode
  title: string
  subtitle?: string
}

export default function Layout({ children, title, subtitle }: LayoutProps) {
  return (
    <div className="min-h-screen flex bg-surface-50">
      {/* Sidebar */}
      <aside className="w-56 flex-shrink-0 border-r border-surface-200 bg-white flex flex-col">
        <div className="px-5 py-5 border-b border-surface-200">
          <h1 className="text-sm font-semibold text-gray-800 leading-tight">
            Modelo SLM Local
          </h1>
          <p className="text-xs text-gray-400 mt-0.5">Fine-tuning wizard</p>
        </div>
        <div className="flex-1 overflow-y-auto scrollbar-thin">
          <Stepper />
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="px-8 py-5 border-b border-surface-200 bg-white">
          <motion.h2
            key={title}
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-xl font-semibold text-gray-900"
          >
            {title}
          </motion.h2>
          {subtitle && (
            <p className="text-sm text-gray-500 mt-0.5">{subtitle}</p>
          )}
        </header>

        {/* Content */}
        <motion.div
          key={title + '-content'}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
          className="flex-1 overflow-y-auto p-8"
        >
          {children}
        </motion.div>
      </main>
    </div>
  )
}
