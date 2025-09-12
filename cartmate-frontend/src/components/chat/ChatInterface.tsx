import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import ChatInput from './ChatInput';
import Welcome from './Welcome';
import AgentIndicator from './AgentIndicator';
import AgentStepSequence from './AgentStepSequence';
import ConnectionStatus from './ConnectionStatus';
import ProductGrid from './ProductGrid';
import PriceComparison from './PriceComparison';
import { CheckoutForm } from './CheckoutForm';
import type { Product } from './types'; // Instead of from './ProductCard'
interface Message {
  id: number;
  text: string;
  sender: 'user' | 'agent' | 'system';
  timestamp: Date;
  isAgentCommunication?: boolean;
  isConnectionStatus?: boolean;
  isProductMessage?: boolean;
  isPriceComparisonMessage?: boolean;
  isCheckoutFormMessage?: boolean;
  products?: Product[];
  priceComparison?: any;
  checkoutFormData?: {
    message: string;
    form_data: {
      email: string;
      address: {
        street_address: string;
        city: string;
        state: string;
        country: string;
        zip_code: string;
      };
      credit_card: {
        number: string;
        cvv: string;
        expiration_year: string;
        expiration_month: string;
      };
    };
  };
  agentSteps?: Array<{
    id: string;
    type: 'calling' | 'processing' | 'success' | 'error';
    agentName: string;
    message: string;
  }>;
  connectionInfo?: {
    sessionId: string;
    userId: string;
    message: string;
  };
}

interface Ad {
  redirect_url: string;
  text: string;
}

interface ChatInterfaceProps {
  onChatStartedChange: (started: boolean) => void;
  onConnectionInfoChange?: (connectionInfo: { sessionId: string; userId: string } | null) => void;
  onAdsUpdate?: (ads: Ad[], context: string[]) => void;
  onAdsLoading?: (loading: boolean) => void;
  newChatTrigger?: number;
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({ onChatStartedChange, onConnectionInfoChange, onAdsUpdate, onAdsLoading, newChatTrigger }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [hasStartedChat, setHasStartedChat] = useState(false);
  const [connectionInfo, setConnectionInfo] = useState<{sessionId: string, userId: string} | null>(null);
  const ws = useRef<WebSocket | null>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Auto-scroll to bottom function
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Auto-scroll when messages change
  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Function to parse agent steps from backend message
  const parseAgentSteps = (agentStepsData: any[]) => {
    if (!agentStepsData || !Array.isArray(agentStepsData)) {
      return null;
    }

    return agentStepsData.map(step => ({
      id: step.id,
      type: step.type as 'calling' | 'processing' | 'success' | 'error',
      agentName: step.agent_name || step.agentName, // Handle both field names
      message: step.message
    }));
  };

  // Function to detect if message contains products
  const detectProducts = (messageData: any): Product[] | null => {
    // Check if the message contains product data
    if (messageData.type === 'text' && messageData.content) {
      // Check if content is an object with products array (new structure from backend)
      if (typeof messageData.content === 'object' && messageData.content.products && Array.isArray(messageData.content.products)) {
        return messageData.content.products as Product[];
      }
      // Check if content is directly an array of products (fallback)
      if (typeof messageData.content === 'object' && Array.isArray(messageData.content)) {
        // Check if it's an array of products
        if (messageData.content.length > 0 && messageData.content[0].id && messageData.content[0].name) {
          return messageData.content as Product[];
        }
      }
    }
    return null;
  };

  // Function to detect if message contains price comparison data
  const detectPriceComparison = (messageData: any): any | null => {
    // Check if the message contains price comparison data
    if (messageData.type === 'text' && messageData.content) {
      // Check if content is an object with price_comparison data
      if (typeof messageData.content === 'object' && messageData.content.price_comparison) {
        return messageData.content.price_comparison;
      }
    }
    return null;
  };

  const detectCheckoutForm = (messageData: any): any | null => {
    // Check if the message contains checkout form data
    if (messageData.type === 'checkout_form' && messageData.content) {
      return messageData.content;
    }
    return null;
  };

  const connectWebSocket = () => {
    try {
      // Don't connect if already connected or connecting
      if (ws.current && (ws.current.readyState === WebSocket.CONNECTING || ws.current.readyState === WebSocket.OPEN)) {
        return;
      }
      
      ws.current = new WebSocket('ws://localhost:8000/ws/chat');

      ws.current.onopen = () => {
        console.log('WebSocket connected');
        setIsLoading(false);
      };
      
      ws.current.onclose = (event) => {
        console.log('WebSocket disconnected', event.code, event.reason);
        setIsLoading(false);
        
        // Auto-reconnect after 3 seconds if it wasn't a clean close
        if (event.code !== 1000 && event.code !== 1012) {
          // Clear any existing timeout
          if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
          }
          
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log('Attempting to reconnect...');
            connectWebSocket();
          }, 3000);
        }
      };

      ws.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setIsLoading(false);
      };

    ws.current.onmessage = (event) => {
      try {
        const messageData = JSON.parse(event.data);
        console.log('Received WebSocket message:', messageData); // Debug log
        
        // Handle connection established message
        if (messageData.type === 'connection_established') {
          console.log('Connection established:', messageData);
          const { session_id, user_id, message } = messageData.content;
          
          // Store connection info
          setConnectionInfo({ sessionId: session_id, userId: user_id });
          
          // Add connection status message
          const connectionMessage: Message = {
            id: Date.now() + Math.random(),
            text: message,
            sender: 'system',
            timestamp: new Date(),
            isConnectionStatus: true,
            connectionInfo: {
              sessionId: session_id,
              userId: user_id,
              message: message
            }
          };
          setMessages(prev => [...prev, connectionMessage]);
          return;
        }
        
        // Handle chat reset message
        if (messageData.type === 'chat_reset') {
          resetChatForNewSession();
          return;
        }
        
        // Handle typing indicator
        if (messageData.type === 'typing_indicator') {
          setIsLoading(messageData.content?.is_typing || false);
          return;
        }
        
        // Handle ads messages
        if (messageData.type === 'ads') {
          const adsData = messageData.content;
          if (adsData && onAdsUpdate) {
            onAdsUpdate(adsData.ads || [], adsData.context || []);
          }
          return;
        }
        
        // Handle agent communication messages
        if (messageData.type === 'agent_communication') {
          console.log('Handling agent_communication message:', messageData);
          // Extract steps from the nested content structure
          const stepsData = messageData.content?.steps || messageData.agent_steps;
          const agentSteps = parseAgentSteps(stepsData);
          if (agentSteps) {
            const agentResponse: Message = {
              id: Date.now() + Math.random(),
              text: messageData.content?.message || "Agent communication in progress",
              sender: 'agent',
              timestamp: new Date(),
              isAgentCommunication: true,
              agentSteps: agentSteps
            };
            setMessages(prev => [...prev, agentResponse]);
            setIsLoading(false);
            return;
          }
        }
        
        // Handle agent communication updates
        if (messageData.type === 'agent_communication_update') {
          console.log('Handling agent_communication_update message:', messageData);
          // Extract steps from the nested content structure
          const stepsData = messageData.content?.steps || messageData.agent_steps;
          const agentSteps = parseAgentSteps(stepsData);
          if (agentSteps) {
            // Check for additional data (price comparison, products, etc.)
            const priceComparison = messageData.content?.price_comparison;
            const products = messageData.content?.products;
            const message = messageData.content?.message;
            
            // Update the last agent communication message instead of adding a new one
            setMessages(prev => {
              const updatedMessages = [...prev];
              // Find the last agent communication message
              for (let i = updatedMessages.length - 1; i >= 0; i--) {
                if (updatedMessages[i].isAgentCommunication) {
                  updatedMessages[i] = {
                    ...updatedMessages[i],
                    agentSteps: agentSteps,
                    text: message || updatedMessages[i].text,
                    isPriceComparisonMessage: priceComparison ? true : updatedMessages[i].isPriceComparisonMessage,
                    isProductMessage: products ? true : updatedMessages[i].isProductMessage,
                    priceComparison: priceComparison || updatedMessages[i].priceComparison,
                    products: products || updatedMessages[i].products
                  };
                  break;
                }
              }
              return updatedMessages;
            });
            setIsLoading(false);
            return;
          }
        }
        
        // Extract text content properly
        let messageText = '';
        if (messageData.type === 'text') {
          // Handle structured message
          if (typeof messageData.content === 'string') {
            messageText = messageData.content;
          } else if (typeof messageData.content === 'object' && messageData.content?.message) {
            messageText = messageData.content.message;
          } else {
            messageText = JSON.stringify(messageData.content);
          }
        } else {
          // Handle other message types
          messageText = messageData.content || JSON.stringify(messageData);
        }
        
        // Check if message contains products, price comparison, or checkout form data
        const products = detectProducts(messageData);
        const priceComparison = detectPriceComparison(messageData);
        const checkoutFormData = detectCheckoutForm(messageData);
        
        // Request contextual ads when products are shown
        if (products && products.length > 0) {
          const categories = products.map(p => p.categories || []).flat();
          const uniqueCategories = [...new Set(categories)];
          if (uniqueCategories.length > 0) {
            setTimeout(() => requestAds(uniqueCategories), 500);
          }
        }
        
        // Check if this is an agent communication update
        const isAgentUpdate = messageData.type === 'agent_communication_update';
        
        // Create agent response with unique ID
        const agentResponse: Message = {
          id: Date.now() + Math.random(), // Ensure unique ID
          text: messageText,
          sender: 'agent',
          timestamp: new Date(),
          isAgentCommunication: isAgentUpdate,
          isProductMessage: products !== null,
          isPriceComparisonMessage: priceComparison !== null,
          isCheckoutFormMessage: checkoutFormData !== null,
          products: products || undefined,
          priceComparison: priceComparison || undefined,
          checkoutFormData: checkoutFormData || undefined
        };
        
        if (isAgentUpdate) {
          // For agent communication updates, try to update existing message
          setMessages(prev => {
            const updatedMessages = [...prev];
            // Find the last agent communication message
            for (let i = updatedMessages.length - 1; i >= 0; i--) {
              if (updatedMessages[i].isAgentCommunication) {
                updatedMessages[i] = {
                  ...updatedMessages[i],
                  ...agentResponse,
                  // Keep existing agent steps if any
                  agentSteps: agentResponse.agentSteps || updatedMessages[i].agentSteps
                };
                return updatedMessages;
              }
            }
            // If no existing agent communication message found, add new one
            return [...prev, agentResponse];
          });
        } else {
          setMessages(prev => [...prev, agentResponse]);
        }
        setIsLoading(false);
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
        // Fallback to treating as plain text
        const agentResponse: Message = {
          id: Date.now() + Math.random(), // Ensure unique ID
          text: event.data,
          sender: 'agent',
          timestamp: new Date()
        };
        setMessages(prev => [...prev, agentResponse]);
        setIsLoading(false);
      }
    };
    } catch (error) {
      console.error('Error setting up WebSocket:', error);
      setIsLoading(false);
      
      // Add an error message to the chat
      const errorMessage: Message = {
        id: Date.now() + Math.random(),
        text: 'Unable to connect to the chat service. Please check if the backend is running and try refreshing the page.',
        sender: 'agent',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    }
  };

  useEffect(() => {
    // Connect to WebSocket on mount
    connectWebSocket();

    return () => {
      if (ws.current) {
        ws.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, []); // Empty array means this runs once on mount

  // Notify parent when chat started state changes
  useEffect(() => {
    onChatStartedChange(hasStartedChat);
  }, [hasStartedChat, onChatStartedChange]);

  // Notify parent when connection info changes
  useEffect(() => {
    if (onConnectionInfoChange) {
      onConnectionInfoChange(connectionInfo);
    }
  }, [connectionInfo, onConnectionInfoChange]);

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
    if (!input.trim() || isLoading || !ws.current || ws.current.readyState !== WebSocket.OPEN) {
      console.warn('Cannot send message: WebSocket not ready');
      return;
    }

    const userMessage = input.trim();
    setInput('');
    setIsLoading(true);
    
    if (!hasStartedChat) {
      setHasStartedChat(true);
      // Request initial ads when chat starts
      setTimeout(() => requestAds(), 1000);
    }

    const newMessage: Message = {
      id: Date.now() + Math.random(), // Ensure unique ID
      text: userMessage,
      sender: 'user',
      timestamp: new Date()
    };
    
    setMessages(prev => [...prev, newMessage]);
    
    // Send message to WebSocket in expected format
    try {
      ws.current.send(userMessage);
    } catch (error) {
      console.error('Error sending message:', error);
      setIsLoading(false);
      // Add error message
      const errorMessage: Message = {
        id: Date.now() + Math.random(),
        text: 'Failed to send message. Please check your connection and try again.',
        sender: 'agent',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    }
  };

  const handleCheckoutFormSubmit = async (formData: any) => {
    if (!ws.current || ws.current.readyState !== WebSocket.OPEN) return;

    try {
      // Send the checkout form data to the backend
      ws.current.send(JSON.stringify({
        type: 'text',
        content: `Checkout with email: ${formData.email}, address: ${formData.address.street_address}, ${formData.address.city}, ${formData.address.state}, ${formData.address.country} ${formData.address.zip_code}, payment: ${formData.credit_card.number}`
      }));
    } catch (error) {
      console.error('Error submitting checkout form:', error);
    }
  };

  const requestAds = (contextKeys: string[] = []) => {
    if (!ws.current || ws.current.readyState !== WebSocket.OPEN) return;
    
    try {
      ws.current.send(JSON.stringify({
        type: 'ads_request',
        content: {
          context_keys: contextKeys
        }
      }));
      
      if (onAdsLoading) {
        onAdsLoading(true);
      }
    } catch (error) {
      console.error('Error requesting ads:', error);
    }
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
                      <div className="flex justify-end mb-4 user-message-enter">
                        <div className="bg-gray-800 text-white rounded-2xl p-3 max-w-[400px] shadow-sm">
                          <p className="text-xs leading-5">{message.text}</p>
                        </div>
                      </div>
                    )}
                    {message.sender === 'agent' && (
                      <div className="mb-4 message-enter">
                        {message.isAgentCommunication && message.agentSteps ? (
                          <div className="w-full">
                            <AgentStepSequence steps={message.agentSteps} />
                            {/* Also show price comparison if available */}
                            {message.isPriceComparisonMessage && message.priceComparison && (
                              <div className="mt-4">
                                <PriceComparison priceComparison={message.priceComparison} />
                              </div>
                            )}
                          </div>
                        ) : message.isPriceComparisonMessage && message.priceComparison ? (
                          <div className="w-full">
                            {/* Show price comparison component */}
                            <PriceComparison priceComparison={message.priceComparison} />
                          </div>
                        ) : message.isCheckoutFormMessage && message.checkoutFormData ? (
                          <div className="w-full">
                            {/* Show checkout form component */}
                            <CheckoutForm 
                              message={message.checkoutFormData.message}
                              formData={message.checkoutFormData.form_data}
                              onSubmit={handleCheckoutFormSubmit}
                            />
                          </div>
                        ) : message.isProductMessage && message.products ? (
                          <div className="w-full">
                            {/* Only show text message if no products are present */}
                            {(!message.products || message.products.length === 0) && (
                              <div className="text-sm font-normal text-left leading-6 max-w-none prose prose-gray max-w-none mb-4">
                                <ReactMarkdown
                                  components={{
                                    p: ({ children }) => <p className="text-left mb-2">{children}</p>,
                                    ul: ({ children }) => <ul className="list-disc pl-4 mb-2">{children}</ul>,
                                    ol: ({ children }) => <ol className="list-decimal pl-4 mb-2">{children}</ol>,
                                    li: ({ children }) => <li className="mb-0.5">{children}</li>,
                                    strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
                                    em: ({ children }) => <em className="italic">{children}</em>,
                                    code: ({ children }) => <code className="bg-gray-100 px-1 py-0.5 rounded text-xs font-mono">{children}</code>,
                                    pre: ({ children }) => <pre className="bg-gray-100 p-3 rounded-lg overflow-x-auto mb-2 text-xs">{children}</pre>,
                                    h1: ({ children }) => <h1 className="text-lg font-bold mb-2">{children}</h1>,
                                    h2: ({ children }) => <h2 className="text-base font-bold mb-1">{children}</h2>,
                                    h3: ({ children }) => <h3 className="text-sm font-bold mb-1">{children}</h3>,
                                    blockquote: ({ children }) => <blockquote className="border-l-4 border-gray-300 pl-3 italic mb-2">{children}</blockquote>,
                                  }}
                                >
                                  {typeof message.text === 'string' ? message.text : JSON.stringify(message.text)}
                                </ReactMarkdown>
                              </div>
                            )}
                            {/* Show products if available */}
                            {message.products && message.products.length > 0 && (
                              <ProductGrid products={message.products} />
                            )}
                          </div>
                        ) : (
                          <div className="w-full text-gray-900">
                            <div className="text-sm font-normal text-left leading-6 max-w-none prose prose-gray max-w-none">
                              <ReactMarkdown
                                components={{
                                  p: ({ children }) => <p className="text-left mb-2">{children}</p>,
                                  ul: ({ children }) => <ul className="list-disc pl-4 mb-2">{children}</ul>,
                                  ol: ({ children }) => <ol className="list-decimal pl-4 mb-2">{children}</ol>,
                                  li: ({ children }) => <li className="mb-0.5">{children}</li>,
                                  strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
                                  em: ({ children }) => <em className="italic">{children}</em>,
                                  code: ({ children }) => <code className="bg-gray-100 px-1 py-0.5 rounded text-xs font-mono">{children}</code>,
                                  pre: ({ children }) => <pre className="bg-gray-100 p-3 rounded-lg overflow-x-auto mb-2 text-xs">{children}</pre>,
                                  h1: ({ children }) => <h1 className="text-lg font-bold mb-2">{children}</h1>,
                                  h2: ({ children }) => <h2 className="text-base font-bold mb-1">{children}</h2>,
                                  h3: ({ children }) => <h3 className="text-sm font-bold mb-1">{children}</h3>,
                                  blockquote: ({ children }) => <blockquote className="border-l-4 border-gray-300 pl-3 italic mb-2">{children}</blockquote>,
                                }}
                              >
                                {typeof message.text === 'string' ? message.text : JSON.stringify(message.text)}
                              </ReactMarkdown>
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                    {message.sender === 'system' && message.isConnectionStatus && message.connectionInfo && (
                      <div className="mb-4 message-enter">
                        <ConnectionStatus
                          sessionId={message.connectionInfo.sessionId}
                          userId={message.connectionInfo.userId}
                          message={message.connectionInfo.message}
                          timestamp={message.timestamp}
                        />
                      </div>
                    )}
                  </div>
                ))}
                {isLoading && (
                  <div className="mb-4">
                    <div className="flex items-center gap-2">
                      <div className="flex items-center gap-1">
                        <div className="w-2 h-2 bg-orange-400 rounded-full animate-bounce"></div>
                        <div className="w-2 h-2 bg-orange-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                        <div className="w-2 h-2 bg-orange-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                      </div>
                      <span className="text-xs text-gray-500 font-medium">CartMate is thinking...</span>
                    </div>
                  </div>
                )}
                {/* Scroll anchor for auto-scroll */}
                <div ref={messagesEndRef} />
              </div>
            </div>
          </div>

          <div className="absolute bottom-0 left-0 right-0 z-10">
            <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-white via-white via-white/90 to-transparent pointer-events-none" />
            
            <div className="relative max-w-[800px] mx-auto p-6 pointer-events-auto">
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