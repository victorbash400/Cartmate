import { useState, useEffect } from 'react'
import { MessagesSquare } from 'lucide-react';
import Sidebar from './components/ui/Sidebar'
import ChatInterface from './components/chat/ChatInterface'
import AgentGroupChat from './components/ui/AgentGroupChat'
import './App.css'

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
    <div className="app-container">
      {!isWelcomeScreenActive && (
        <Sidebar isOpen={isSidebarOpen} toggleSidebar={toggleSidebar} />
      )}
      
      <div className="main-content">
        <ChatInterface onChatStartedChange={handleChatStartedChange} />
        {!isWelcomeScreenActive && (
          <AgentGroupChat 
            isVisible={isAgentGroupVisible} 
            toggleVisibility={toggleAgentGroup} 
          />
        )}
        
        {!isWelcomeScreenActive && (
          <button 
            className="agent-chat-toggle-new" 
            onClick={toggleAgentGroup}
            title={isAgentGroupVisible ? 'Hide Agent Chat' : 'Show Agent Chat'}
          >
            <MessagesSquare size={24} color="#FF9E00" />
            {!isAgentGroupVisible && <span style={{ marginLeft: '8px' }}>Agent Groupchat</span>}
          </button>
        )}
      </div>
    </div>
  )
}

export default App
