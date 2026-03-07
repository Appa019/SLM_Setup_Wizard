import { motion } from 'framer-motion'

interface ChatMessageProps {
  role: 'user' | 'assistant'
  content: string
}

export default function ChatMessage({ role, content }: ChatMessageProps) {
  const isUser = role === 'user'
  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-2`}
    >
      {!isUser && (
        <div className="w-6 h-6 rounded-sm bg-accent-500 flex items-center justify-center mr-2 mt-0.5 flex-shrink-0">
          <span className="text-white font-bold text-[10px]">S</span>
        </div>
      )}
      <div
        className={`max-w-[72%] px-3 py-2 text-sm leading-relaxed whitespace-pre-wrap rounded
          ${isUser
            ? 'bg-accent-500 text-white'
            : 'bg-white border border-surface-200 text-gray-800 shadow-card'
          }`}
      >
        {content}
      </div>
    </motion.div>
  )
}
