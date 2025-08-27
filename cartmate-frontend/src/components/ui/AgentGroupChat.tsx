import React, { useState, useRef, useEffect } from 'react';
import ChatInput from '../chat/ChatInput';
import Welcome from '../chat/Welcome';
import './AgentGroupChat.css';

interface Message {
  id: number;
  text: string;
  sender: 'user' | 'agent';
  timestamp: Date;
}

interface AgentGroupChatProps {
  isVisible: boolean;
  toggleVisibility: () => void;
}

const AgentGroupChat: React.FC<AgentGroupChatProps> = ({ isVisible, toggleVisibility }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [hasStartedChat, setHasStartedChat] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth <= 768);
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  const handleOverlayClick = () => {
    if (isMobile) {
      toggleVisibility();
    }
  };

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
    <>
      {/* Mobile overlay */}
      {isMobile && (
        <div 
          className={`agent-group-overlay ${isVisible ? 'active' : ''}`}
          onClick={handleOverlayClick}
        />
      )}
      
      <div className={`agent-group-chat ${isVisible ? 'visible' : ''}`}>
        {!hasStartedChat ? (
          // Welcome state - centered input
          <div className="agent-group-welcome">
            <Welcome
              input={input}
              onInputChange={setInput}
              onSubmit={handleSendMessage}
              isLoading={isLoading}
            />
          </div>
        ) : (
          // Normal chat state
          <>
            {/* Messages area */}
            <div ref={chatContainerRef} className="agent-group-messages-container">
              <div className="agent-group-messages-wrapper">
                <div className="messages-list">
                  {messages.map((message) => (
                    <div key={message.id}>
                      {message.sender === 'user' && (
                        <div className="user-message-container">
                          <div className="user-message-bubble">
                            <p className="message-text">{message.text}</p>
                          </div>
                        </div>
                      )}
                      {message.sender === 'agent' && (
                        <div className="agent-message-container">
                          <div className="agent-message-content">
                            <div className="agent-message-text">
                              <p className="message-paragraph">{message.text}</p>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                  {isLoading && (
                    <div className="loading-container">
                      <div className="loading-dots">
                        <div className="loading-dot"></div>
                        <div className="loading-dot"></div>
                        <div className="loading-dot"></div>
                      </div>
                      <span className="loading-text">Thinking...</span>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Floating bottom chat input */}
            <div className="agent-group-input-container">
              <div className="agent-group-input-wrapper">
                <ChatInput
                  value={input}
                  onChange={setInput}
                  onSubmit={handleSendMessage}
                  placeholder=""  // Empty placeholder to remove the hint
                  disabled={isLoading}
                  isLoading={isLoading}
                />
              </div>
            </div>
          </>
        )}
      </div>
    </>
  );
};

export default AgentGroupChat;