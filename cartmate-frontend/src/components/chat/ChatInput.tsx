import { useState, useRef, useEffect } from 'react';
import { ArrowRight, Plus } from 'lucide-react';
import './ChatInput.css';

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
    <div className="chat-input-container">
      <button
        type="button"
        className="chat-input-button"
        disabled={disabled}
      >
        <Plus size={16} color="#FF9E00" />
      </button>
      <textarea
        ref={textareaRef}
        value={value}
        onChange={handleInputChange}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        rows={1}
        className="chat-input-textarea"
      />
      <button
        onClick={onSubmit}
        disabled={disabled || !value.trim()}
        className="send-button"
      >
        {isLoading ? (
          <div className="loading-spinner" />
        ) : (
          <ArrowRight size={16} color="#FF9E00" />
        )}
      </button>
    </div>
  );
}