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

  return (
    <div className="app-container">
      <Sidebar isOpen={isSidebarOpen} toggleSidebar={toggleSidebar} />
      
      <div className="main-content">
        <ChatInterface onChatStartedChange={() => {}} />
        <AgentGroupChat 
          isVisible={isAgentGroupVisible} 
          toggleVisibility={toggleAgentGroup} 
        />
        
        <button 
          className="agent-chat-toggle-new" 
          onClick={toggleAgentGroup}
          title={isAgentGroupVisible ? 'Hide Chat' : 'Show Chat'}
        >
          <MessagesSquare size={24} color="#FF9E00" />
          {!isAgentGroupVisible && <span style={{ marginLeft: '8px' }}>Chat</span>}
        </button>
      </div>
    </div>
  )
}

export default App
