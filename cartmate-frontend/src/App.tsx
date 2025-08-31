import { useState, useEffect } from 'react'
import { MessagesSquare } from 'lucide-react';
import Sidebar from './components/ui/Sidebar'
import ChatInterface from './components/chat/ChatInterface'
import AgentGroupChat from './components/ui/AgentGroupChat'

function App() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const [isAgentGroupVisible, setIsAgentGroupVisible] = useState(false)
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

  return (
    <div className="flex h-screen w-screen bg-gray-100 overflow-hidden">
      {!isWelcomeScreenActive && (
        <Sidebar isOpen={isSidebarOpen} toggleSidebar={toggleSidebar} />
      )}
      
      <div className="flex-grow flex relative h-full overflow-y-auto">
        <ChatInterface onChatStartedChange={handleChatStartedChange} />
        {!isWelcomeScreenActive && (
          <AgentGroupChat 
            isVisible={isAgentGroupVisible} 
            toggleVisibility={toggleAgentGroup} 
          />
        )}
        
        {!isWelcomeScreenActive && (
          <button 
            className="absolute top-5 right-5 flex items-center py-2.5 px-4 bg-white border border-gray-300 rounded-full cursor-pointer shadow-md transition-all duration-300 hover:shadow-lg hover:-translate-y-0.5 z-50"
            onClick={toggleAgentGroup}
            title={isAgentGroupVisible ? 'Hide Agent Chat' : 'Show Agent Chat'}
          >
            <MessagesSquare size={24} color="#FF9E00" />
            {!isAgentGroupVisible && <span className="ml-2">Agent Groupchat</span>}
          </button>
        )}
      </div>
    </div>
  )
}

export default App
