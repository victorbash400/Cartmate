import { useState, useEffect } from 'react'
import { MessageCircle } from 'lucide-react';
import Sidebar from './components/ui/Sidebar'
import ChatInterface from './components/chat/ChatInterface'
import { InlineAds } from './components/ads'

interface Ad {
  redirect_url: string;
  text: string;
}

function App() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const [newChatTrigger, setNewChatTrigger] = useState(0)
  const [connectionInfo, setConnectionInfo] = useState<{ sessionId: string; userId: string } | null>(null)
  const [ads, setAds] = useState<Ad[]>([])
  const [adsContext, setAdsContext] = useState<string[]>([])
  const [adsLoading, setAdsLoading] = useState(false)
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

  const handleAdsUpdate = (newAds: Ad[], context: string[]) => {
    setAds(newAds);
    setAdsContext(context);
    setAdsLoading(false);
  }

  const handleAdsLoading = (loading: boolean) => {
    setAdsLoading(loading);
  }

  return (
    <div className="flex h-screen w-screen bg-gray-100 overflow-hidden">
      {!isWelcomeScreenActive && (
        <Sidebar isOpen={isSidebarOpen} toggleSidebar={toggleSidebar} connectionInfo={connectionInfo} />
      )}
      
      <div className="flex-grow flex relative h-full overflow-y-auto">
        <div className="flex-1">
          <ChatInterface 
            onChatStartedChange={handleChatStartedChange} 
            onConnectionInfoChange={handleConnectionInfoChange}
            onAdsUpdate={handleAdsUpdate}
            onAdsLoading={handleAdsLoading}
            newChatTrigger={newChatTrigger} 
          />
        </div>
        
        {!isWelcomeScreenActive && (
          <>
            {/* Compact Ads Component - Middle Right */}
            <div className="w-64 p-4 flex flex-col justify-center">
              <InlineAds 
                ads={ads}
                context={adsContext}
                isLoading={adsLoading}
              />
            </div>
            
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
          </>
        )}
      </div>
    </div>
  )
}

export default App
