import { motion } from 'framer-motion'

interface LoaderProps {
  message?: string
}

export default function Loader({ message }: LoaderProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-16">
      <motion.div
        className="w-10 h-10 rounded-full border-2 border-accent-500 border-t-transparent"
        animate={{ rotate: 360 }}
        transition={{ repeat: Infinity, duration: 0.8, ease: 'linear' }}
      />
      {message && (
        <p className="text-sm text-gray-500 animate-pulse">{message}</p>
      )}
    </div>
  )
}
