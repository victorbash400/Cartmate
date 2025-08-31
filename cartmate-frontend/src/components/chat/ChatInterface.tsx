import React, { useState, useRef, useEffect } from 'react';
import ChatInput from './ChatInput';
import Welcome from './Welcome';

interface Message {
  id: number;
  text: string;
  sender: 'user' | 'agent';
  timestamp: Date;
}

interface ChatInterfaceProps {
  onChatStartedChange: (started: boolean) => void;
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({ onChatStartedChange }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [hasStartedChat, setHasStartedChat] = useState(false);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  // Notify parent when chat started state changes
  useEffect(() => {
    onChatStartedChange(hasStartedChat);
  }, [hasStartedChat, onChatStartedChange]);

  const handleSendMessage = () => {
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput('');
    setIsLoading(true);
    
    // Mark that chat has started
    if (!hasStartedChat) {
      setHasStartedChat(true);
    }

    const newMessage: Message = {
      id: messages.length + 1,
      text: userMessage,
      sender: 'user',
      timestamp: new Date()
    };
    
    setMessages(prev => [...prev, newMessage]);
    
    // Simulate agent response after a short delay
    setTimeout(() => {
      const agentResponse: Message = {
        id: messages.length + 2,
        text: `Thanks for your message: "${userMessage}". This is a simulated response.`,
        sender: 'agent',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, agentResponse]);
      setIsLoading(false);
    }, 1000);
  };

  return (
    <div className={`flex flex-col h-full w-full relative ${hasStartedChat ? 'chat-started' : 'welcome-state'}`}>
      {!hasStartedChat ? (
        // Welcome state - centered input
        <Welcome
          input={input}
          onInputChange={setInput}
          onSubmit={handleSendMessage}
          isLoading={isLoading}
        />
      ) : (
        // Normal chat state
        <>
          {/* Messages area */}
          <div ref={chatContainerRef} className="h-full overflow-y-auto pb-32">
            <div className="max-w-[600px] mx-auto p-8">
              <div className="flex flex-col gap-8">
                {messages.map((message) => (
                  <div key={message.id}>
                    {message.sender === 'user' && (
                      <div className="flex justify-end mb-8">
                        <div className="bg-gray-800 text-white rounded-3xl p-5 max-w-[448px] shadow-sm">
                          <p className="text-sm leading-6">{message.text}</p>
                        </div>
                      </div>
                    )}
                    {message.sender === 'agent' && (
                      <div className="mb-8">
                        <div className="w-full text-gray-900">
                          <div className="text-lg font-normal text-left leading-7 max-w-none">
                            <p className="text-left mb-4">{message.text}</p>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
                {isLoading && (
                  <div className="mb-8">
                    <div className="flex items-center gap-1 mr-3">
                      <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-pulse"></div>
                      <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></div>
                      <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-pulse" style={{ animationDelay: '0.4s' }}></div>
                    </div>
                    <span className="text-sm text-gray-500">Thinking...</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Floating bottom chat input with fade from bottom */}
          <div className="absolute bottom-0 left-0 right-0 z-10">
            {/* Fade overlay from bottom of page up to behind input */}
            <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-white via-white via-white/90 to-transparent pointer-events-none" />
            
            {/* Input area on top of fade */}
            <div className="relative max-w-[600px] mx-auto p-6 pointer-events-auto">
              <ChatInput
                value={input}
                onChange={setInput}
                onSubmit={handleSendMessage}
                placeholder="Continue the conversation..."
                disabled={isLoading}
                isLoading={isLoading}
              />
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default ChatInterface;