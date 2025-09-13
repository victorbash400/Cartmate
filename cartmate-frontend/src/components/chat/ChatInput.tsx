import { useRef, useEffect } from 'react'
import { ArrowRight, Plus } from 'lucide-react'

interface ChatInputProps {
  value: string
  onChange: (value: string) => void
  onSubmit: () => void
  onKeyDown?: (e: React.KeyboardEvent) => void
  placeholder?: string
  disabled?: boolean
  isLoading?: boolean
}

export default function ChatInput({
  value,
  onChange,
  onSubmit,
  onKeyDown,
  placeholder = "Continue the conversation...",
  disabled = false,
  isLoading = false
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Auto-resize textarea
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    onChange(e.target.value)
    
    const textarea = e.target
    textarea.style.height = 'auto'
    textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px'
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      onSubmit()
    }
    onKeyDown?.(e)
  }

  useEffect(() => {
    if (!value && textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }, [value])

  return (
    <div className="flex items-end space-x-2 px-4 py-3 bg-white border border-gray-200 rounded-2xl shadow-sm hover:border-gray-300 hover:shadow-md focus-within:border-gray-400 focus-within:shadow-lg transition-all duration-300 ease-out">
      <button
        type="button"
        className="flex-shrink-0 w-8 h-8 rounded-xl bg-gray-50 hover:bg-gray-100 transition-all duration-200 flex items-center justify-center hover:scale-105 active:scale-95"
        disabled={disabled}
      >
        <Plus className="w-4 h-4 text-gray-500" />
      </button>
      
      <textarea
        ref={textareaRef}
        value={value}
        onChange={handleInputChange}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        rows={1}
        className="flex-1 bg-transparent text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-0 focus:border-none text-sm font-normal resize-none leading-6 py-1"
        style={{
          outline: 'none',
          boxShadow: 'none',
          border: 'none',
          minHeight: '32px',
          maxHeight: '120px'
        }}
      />
      
      <button
        onClick={onSubmit}
        disabled={disabled || !value.trim()}
        className="flex-shrink-0 w-8 h-8 rounded-xl bg-black hover:bg-gray-800 disabled:bg-gray-200 disabled:cursor-not-allowed transition-all duration-200 flex items-center justify-center shadow-sm hover:scale-105 active:scale-95 mb-0.5"
      >
        {isLoading ? (
          <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
        ) : (
          <ArrowRight className="w-4 h-4 text-white" />
        )}
      </button>
    </div>
  )
}
