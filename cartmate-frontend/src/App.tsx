import { useState, useEffect } from 'react'
import { MessagesSquare, MessageCircle } from 'lucide-react';
import Sidebar from './components/ui/Sidebar'
import ChatInterface from './components/chat/ChatInterface'
import AgentGroupChat from './components/ui/AgentGroupChat'

function App() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const [isAgentGroupVisible, setIsAgentGroupVisible] = useState(false)
  const [newChatTrigger, setNewChatTrigger] = useState(0)
  const [connectionInfo, setConnectionInfo] = useState<{ sessionId: string; userId: string } | null>(null)
  useEffect(() => {
    const checkMobile = () => {
      const mobile = window.innerWidth <= 768;
      // Close sidebar by default on mobile
      if (mobile && isSidebarOpen) {
        setIsSidebarOpen(false);
      }
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, [isSidebarOpen]);

  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen)
  }

  const toggleAgentGroup = () => {
    setIsAgentGroupVisible(!isAgentGroupVisible)
  }

  const [isWelcomeScreenActive, setIsWelcomeScreenActive] = useState(true)

  const handleChatStartedChange = (started: boolean) => {
    setIsWelcomeScreenActive(!started);
  }

  const handleNewChat = () => {
    setNewChatTrigger(prev => prev + 1);
  }

  const handleConnectionInfoChange = (info: { sessionId: string; userId: string } | null) => {
    setConnectionInfo(info);
  }

  return (
    <div className="flex h-screen w-screen bg-gray-100 overflow-hidden">
      {!isWelcomeScreenActive && (
        <Sidebar isOpen={isSidebarOpen} toggleSidebar={toggleSidebar} connectionInfo={connectionInfo} />
      )}
      
      <div className="flex-grow flex relative h-full overflow-y-auto">
        <ChatInterface 
          onChatStartedChange={handleChatStartedChange} 
          onConnectionInfoChange={handleConnectionInfoChange}
          newChatTrigger={newChatTrigger} 
        />
        {!isWelcomeScreenActive && (
          <AgentGroupChat 
            isVisible={isAgentGroupVisible} 
            toggleVisibility={toggleAgentGroup} 
          />
        )}
        
        {!isWelcomeScreenActive && (
          <>
            {/* Floating New Chat Button - Top Left */}
            <button 
              className={`absolute top-4 flex items-center py-1.5 px-3 bg-black text-white rounded-md cursor-pointer transition-all duration-200 hover:bg-gray-800 z-50 ${
                isSidebarOpen ? 'left-72' : 'left-20'
              }`}
              onClick={handleNewChat}
              title="Start New Chat"
            >
              <MessageCircle size={14} />
              <span className="ml-1.5 text-xs font-medium">New</span>
            </button>

            {/* Agent Group Chat Button - Top Right */}
            <button 
              className="absolute top-4 right-4 flex items-center py-1.5 px-3 bg-black text-white rounded-md cursor-pointer transition-all duration-200 hover:bg-gray-800 z-50"
              onClick={toggleAgentGroup}
              title={isAgentGroupVisible ? 'Hide Agent Chat' : 'Show Agent Chat'}
            >
              <MessagesSquare size={14} />
              {!isAgentGroupVisible && <span className="ml-1.5 text-xs font-medium">Agents</span>}
            </button>
          </>
        )}
      </div>
    </div>
  )
}

export default App
