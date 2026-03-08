import { motion } from 'framer-motion'

interface LoaderProps {
  message?: string
  size?: 'sm' | 'md'
}

export default function Loader({ message, size = 'md' }: LoaderProps) {
  const dim = size === 'sm' ? 'w-5 h-5' : 'w-8 h-8'
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-12">
      <div className={`${dim} border border-accent-500 relative overflow-hidden`}>
        <motion.div
          className="absolute left-0 right-0 h-[2px] bg-accent-500"
          animate={{ top: ['0%', '100%', '0%'] }}
          transition={{ repeat: Infinity, duration: 1.5, ease: 'linear' }}
        />
      </div>
      {message && (
        <p className="text-xs text-gray-500 font-display tracking-wide">{message}</p>
      )}
    </div>
  )
}
