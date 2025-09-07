import { useState, useEffect } from 'react'
import { MessagesSquare, MessageCircle } from 'lucide-react';
import Sidebar from './components/ui/Sidebar'
import ChatInterface from './components/chat/ChatInterface'
import AgentGroupChat from './components/ui/AgentGroupChat'

function App() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const [isAgentGroupVisible, setIsAgentGroupVisible] = useState(false)
  const [newChatTrigger, setNewChatTrigger] = useState(0)
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

  return (
    <div className="flex h-screen w-screen bg-gray-100 overflow-hidden">
      {!isWelcomeScreenActive && (
        <Sidebar isOpen={isSidebarOpen} toggleSidebar={toggleSidebar} />
      )}
      
      <div className="flex-grow flex relative h-full overflow-y-auto">
        <ChatInterface onChatStartedChange={handleChatStartedChange} newChatTrigger={newChatTrigger} />
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
              className={`absolute top-5 flex items-center py-2.5 px-4 bg-white border border-gray-300 rounded-full cursor-pointer shadow-md transition-all duration-300 hover:shadow-lg hover:-translate-y-0.5 z-50 ${
                isSidebarOpen ? 'left-72' : 'left-20'
              }`}
              onClick={handleNewChat}
              title="Start New Chat"
            >
              <MessageCircle size={20} color="#FF9E00" />
              <span className="ml-2 font-medium text-gray-700">New Chat</span>
            </button>

            {/* Agent Group Chat Button - Top Right */}
            <button 
              className="absolute top-5 right-5 flex items-center py-2.5 px-4 bg-white border border-gray-300 rounded-full cursor-pointer shadow-md transition-all duration-300 hover:shadow-lg hover:-translate-y-0.5 z-50"
              onClick={toggleAgentGroup}
              title={isAgentGroupVisible ? 'Hide Agent Chat' : 'Show Agent Chat'}
            >
              <MessagesSquare size={24} color="#FF9E00" />
              {!isAgentGroupVisible && <span className="ml-2">Agent Groupchat</span>}
            </button>
          </>
        )}
      </div>
    </div>
  )
}

export default App
