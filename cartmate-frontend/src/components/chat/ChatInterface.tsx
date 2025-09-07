import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
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
  newChatTrigger?: number;
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({ onChatStartedChange, newChatTrigger }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [hasStartedChat, setHasStartedChat] = useState(false);
  const ws = useRef<WebSocket | null>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Connect to WebSocket
    ws.current = new WebSocket('ws://localhost:8000/ws/chat');

    ws.current.onopen = () => console.log('WebSocket connected');
    ws.current.onclose = () => console.log('WebSocket disconnected');

    ws.current.onmessage = (event) => {
      try {
        const messageData = JSON.parse(event.data);
        
        // Handle chat reset message
        if (messageData.type === 'chat_reset') {
          resetChatForNewSession();
          return;
        }
        
        // Handle regular agent response
        const agentResponse: Message = {
          id: messages.length + 2, // This could be improved
          text: messageData.content || event.data,
          sender: 'agent',
          timestamp: new Date()
        };
        setMessages(prev => [...prev, agentResponse]);
        setIsLoading(false);
      } catch (error) {
        // Fallback to treating as plain text
        const agentResponse: Message = {
          id: messages.length + 2,
          text: event.data,
          sender: 'agent',
          timestamp: new Date()
        };
        setMessages(prev => [...prev, agentResponse]);
        setIsLoading(false);
      }
    };

    return () => {
      ws.current?.close();
    };
  }, []); // Empty array means this runs once on mount

  // Notify parent when chat started state changes
  useEffect(() => {
    onChatStartedChange(hasStartedChat);
  }, [hasStartedChat, onChatStartedChange]);

  const resetChatForNewSession = () => {
    setMessages([]);
    setInput('');
    setIsLoading(false);
    // Keep chat interface active, don't go back to welcome screen
  };

  const resetChat = () => {
    setMessages([]);
    setInput('');
    setIsLoading(false);
    setHasStartedChat(false);
  };

  const handleNewChat = () => {
    // Immediately reset the UI to provide instant feedback but keep chat interface
    resetChatForNewSession();
    
    // Silently reset the backend session without expecting a response
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({
        type: 'new_chat_silent',
        content: 'reset_session_context'
      }));
    }
  };

  // Listen for new chat trigger from parent
  useEffect(() => {
    if (newChatTrigger && newChatTrigger > 0) {
      handleNewChat();
    }
  }, [newChatTrigger]);

  const handleSendMessage = () => {
    if (!input.trim() || isLoading || !ws.current) return;

    const userMessage = input.trim();
    setInput('');
    setIsLoading(true);
    
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
    
    // Send message to WebSocket
    ws.current.send(userMessage);
  };

  return (
    <div className={`flex flex-col h-full w-full relative ${hasStartedChat ? 'chat-started' : 'welcome-state'}`}>
      {!hasStartedChat ? (
        <Welcome
          input={input}
          onInputChange={setInput}
          onSubmit={handleSendMessage}
          isLoading={isLoading}
        />
      ) : (
        <>
          <div ref={chatContainerRef} className="h-full overflow-y-auto pb-32 hide-scrollbar">
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
                          <div className="text-lg font-normal text-left leading-7 max-w-none prose prose-gray max-w-none">
                            <ReactMarkdown
                              components={{
                                p: ({ children }) => <p className="text-left mb-4">{children}</p>,
                                ul: ({ children }) => <ul className="list-disc pl-6 mb-4">{children}</ul>,
                                ol: ({ children }) => <ol className="list-decimal pl-6 mb-4">{children}</ol>,
                                li: ({ children }) => <li className="mb-1">{children}</li>,
                                strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
                                em: ({ children }) => <em className="italic">{children}</em>,
                                code: ({ children }) => <code className="bg-gray-100 px-1 py-0.5 rounded text-sm font-mono">{children}</code>,
                                pre: ({ children }) => <pre className="bg-gray-100 p-4 rounded-lg overflow-x-auto mb-4">{children}</pre>,
                                h1: ({ children }) => <h1 className="text-2xl font-bold mb-4">{children}</h1>,
                                h2: ({ children }) => <h2 className="text-xl font-bold mb-3">{children}</h2>,
                                h3: ({ children }) => <h3 className="text-lg font-bold mb-2">{children}</h3>,
                                blockquote: ({ children }) => <blockquote className="border-l-4 border-gray-300 pl-4 italic mb-4">{children}</blockquote>,
                              }}
                            >
                              {message.text}
                            </ReactMarkdown>
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

          <div className="absolute bottom-0 left-0 right-0 z-10">
            <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-white via-white via-white/90 to-transparent pointer-events-none" />
            
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