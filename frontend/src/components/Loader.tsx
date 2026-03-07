import { motion } from 'framer-motion'

interface LoaderProps {
  message?: string
  size?: 'sm' | 'md'
}

export default function Loader({ message, size = 'md' }: LoaderProps) {
  const dim = size === 'sm' ? 'w-5 h-5' : 'w-8 h-8'
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-12">
      <motion.div
        className={`${dim} rounded-sm border-2 border-accent-500 border-t-transparent`}
        animate={{ rotate: 360 }}
        transition={{ repeat: Infinity, duration: 0.75, ease: 'linear' }}
      />
      {message && (
        <p className="text-xs text-gray-500">{message}</p>
      )}
    </div>
  )
}
