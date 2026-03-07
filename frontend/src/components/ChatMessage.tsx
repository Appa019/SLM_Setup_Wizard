import { motion } from 'framer-motion'

interface ChatMessageProps {
  role: 'user' | 'assistant'
  content: string
}

export default function ChatMessage({ role, content }: ChatMessageProps) {
  const isUser = role === 'user'
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3`}
    >
      <div
        className={`max-w-[75%] px-4 py-2.5 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap
          ${isUser
            ? 'bg-accent-500 text-white rounded-br-sm'
            : 'bg-white border border-surface-200 text-gray-800 rounded-bl-sm shadow-sm'
          }`}
      >
        {content}
      </div>
    </motion.div>
  )
}
