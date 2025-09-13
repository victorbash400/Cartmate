import React, { useState, useEffect } from 'react'
import { MessageCircle } from 'lucide-react';
import Sidebar from './components/ui/Sidebar'
import ChatInterface from './components/chat/ChatInterface'
// Safe ads component that won't break the app
const SafeInlineAds: React.FC<{ads: any[], context: string[], isLoading: boolean}> = ({ ads, context, isLoading }) => {
  const [AdComponent, setAdComponent] = useState<React.ComponentType<any> | null>(null);
  const [loadError, setLoadError] = useState(false);

  useEffect(() => {
    // Try to load the ads component
    import('./components/promotions')
      .then(module => {
        setAdComponent(() => module.InlineAds);
      })
      .catch(() => {
        setLoadError(true);
      });
  }, []);

  // If there's an error loading or ad blocker detected, show fallback
  if (loadError) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-5 h-5 bg-gray-100 rounded-full flex items-center justify-center">
            <span className="text-gray-400 text-xs">•</span>
          </div>
          <h3 className="text-sm font-medium text-gray-600">Content</h3>
        </div>
        <div className="text-center text-gray-500 text-sm py-4">
          Content loading...
        </div>
      </div>
    );
  }

  // If component loaded successfully, render it
  if (AdComponent) {
    return <AdComponent ads={ads} context={context} isLoading={isLoading} />;
  }

  // Loading state
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
      <div className="text-center text-gray-500 text-sm py-4">Loading...</div>
    </div>
  );
};

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
              <SafeInlineAds 
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
