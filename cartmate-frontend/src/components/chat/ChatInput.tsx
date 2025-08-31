import { useState, useRef, useEffect } from 'react';
import { ArrowRight, Plus } from 'lucide-react';

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  onKeyDown?: (e: React.KeyboardEvent) => void;
  placeholder?: string;
  disabled?: boolean;
  isLoading?: boolean;
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
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    onChange(e.target.value);
    const textarea = e.target;
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px';
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSubmit();
    }
    onKeyDown?.(e);
  };

  useEffect(() => {
    if (!value && textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [value]);

  return (
    <div className="flex items-end gap-3 p-2.5 bg-white border-2 border-orange-400 rounded-2xl shadow-lg transition-all duration-300 hover:border-orange-400 hover:shadow-xl focus-within:border-orange-600 focus-within:shadow-2xl">
      {/* Add Button */}
      <button
        type="button"
        className="flex-shrink-0 w-8 h-8 rounded-full bg-white border border-orange-400 cursor-pointer flex items-center justify-center transition-colors duration-200 hover:bg-orange-50 disabled:cursor-not-allowed disabled:opacity-50"
        disabled={disabled}
      >
        <Plus size={16} color="#FF9E00" />
      </button>

      {/* Input Area */}
      <textarea
        ref={textareaRef}
        value={value}
        onChange={handleInputChange}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        rows={1}
        className="flex-1 bg-white text-gray-900 border-none outline-none text-base font-normal resize-none leading-6 p-1 min-h-6 max-h-[150px] placeholder-gray-500 focus:outline-none"
      />

      {/* Send Button */}
      <button
        onClick={onSubmit}
        disabled={disabled || !value.trim()}
        className="flex-shrink-0 w-9 h-9 rounded-full bg-white border border-orange-400 cursor-pointer flex items-center justify-center shadow-sm transition-all duration-200 mb-1 hover:bg-orange-50 hover:scale-110 active:scale-95 disabled:bg-gray-50 disabled:border-gray-200 disabled:cursor-not-allowed disabled:transform-none"
      >
        {isLoading ? (
          <div className="w-3 h-3 border-2 border-gray-400 border-opacity-30 border-t-2 border-t-gray-600 rounded-full animate-spin" />
        ) : (
          <ArrowRight size={16} color="#FF9E00" />
        )}
      </button>
    </div>
  );
}
