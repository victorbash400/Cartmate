import React, { useEffect, useState } from 'react';
import { CircleChevronLeft, CircleChevronRight, User, LogOut, PersonStanding, ShoppingBag } from 'lucide-react';
import PersonalizationModal from './PersonalizationModal';

interface SidebarProps {
  isOpen: boolean;
  toggleSidebar: () => void;
  connectionInfo?: { sessionId: string; userId: string } | null;
}

const Sidebar: React.FC<SidebarProps> = ({ isOpen, toggleSidebar, connectionInfo }) => {
  const [isMobile, setIsMobile] = useState(false);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isPersonalizationModalOpen, setIsPersonalizationModalOpen] = useState(false);

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
      toggleSidebar();
    }
  };


  const handleLogin = () => {
    setIsLoggedIn(true);
    console.log('User logged in');
  };

  const handleLogout = () => {
    setIsLoggedIn(false);
    console.log('User logged out');
  };

  const handleCartClick = () => {
    console.log('Cart clicked');
  };

  const handlePersonalizationClick = () => {
    setIsPersonalizationModalOpen(true);
  };

  const handlePersonalizationSave = async (data: any) => {
    try {
      if (!connectionInfo?.sessionId) {
        throw new Error('No session ID available');
      }

      const formData = new FormData();
      formData.append('session_id', connectionInfo.sessionId);
      
      if (data.stylePreferences) {
        formData.append('style_preferences', data.stylePreferences);
      }
      
      if (data.budgetRange) {
        formData.append('budget_min', data.budgetRange.min.toString());
        formData.append('budget_max', data.budgetRange.max.toString());
      }
      
      if (data.image) {
        formData.append('image', data.image);
      }

      const response = await fetch('http://localhost:8000/api/personalization/save', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      console.log('Personalization data saved successfully:', result);
      
    } catch (error) {
      console.error('Error saving personalization data:', error);
      throw error; // Re-throw to show error in modal
    }
  };

  // Improved button style with better spacing and hover effects
  const sidebarButton = (children: React.ReactNode, onClick?: () => void, title?: string) => (
    <button
      className={`flex items-center gap-3 py-2.5 px-3 rounded-lg cursor-pointer transition-all duration-200 text-gray-700 hover:bg-gray-50 hover:text-gray-900 active:bg-gray-100
      ${isOpen ? 'w-full justify-start' : 'w-10 h-10 mx-auto justify-center p-0'}`}
      onClick={onClick}
      title={title}
    >
      {children}
    </button>
  );

  return (
    <>
      {/* Mobile overlay */}
      {isMobile && (
        <div
          className={`fixed top-0 left-0 w-full h-full bg-black bg-opacity-20 z-40 transition-opacity duration-300 ${
            isOpen ? 'opacity-100 visible' : 'opacity-0 invisible'
          }`}
          onClick={handleOverlayClick}
        />
      )}

      <div
        className={`relative h-screen bg-white border-r border-gray-200 transition-all duration-300 ease-in-out flex flex-col flex-shrink-0
        ${isOpen ? 'w-64' : 'w-16'}
        ${isMobile ? 'fixed top-0 left-0 z-50 transform transition-transform duration-300 ' + (isOpen ? 'translate-x-0' : '-translate-x-full') : ''}`}
      >
        {/* Header section with brand and toggle */}
        <div className="relative px-4 py-4 border-b border-gray-100">
          <h2
            className={`text-gray-800 text-lg font-semibold whitespace-nowrap overflow-hidden transition-all duration-300 ${
              isOpen ? 'opacity-100' : 'opacity-0 w-0'
            }`}
          >
            CartMate
          </h2>

          {/* Toggle button */}
          <button
            className="absolute top-4 right-4 bg-transparent border-none cursor-pointer text-gray-600 hover:text-gray-800 p-1 rounded-full hover:bg-gray-100 w-8 h-8 flex items-center justify-center transition-colors duration-200"
            onClick={toggleSidebar}
          >
            {isOpen ? (
              <CircleChevronLeft size={18} color="#FF9E00" />
            ) : (
              <CircleChevronRight size={18} color="#FF9E00" />
            )}
          </button>
        </div>

        {/* Menu Items with proper spacing */}
        <div className="flex-1 px-3 py-4">
          <div className="space-y-1">
            {sidebarButton(
              <>
                <PersonStanding size={20} color="#FF9E00" className="shrink-0" />
                {isOpen && <span className="font-medium whitespace-nowrap">Personalization</span>}
              </>,
              handlePersonalizationClick,
              'Personalization'
            )}


            {sidebarButton(
              <>
                <ShoppingBag size={20} color="#FF9E00" className="shrink-0" />
                {isOpen && <span className="font-medium whitespace-nowrap">Cart</span>}
              </>,
              handleCartClick,
              'Cart'
            )}
          </div>
        </div>

        {/* Connection info section */}
        {connectionInfo && (
          <div className="border-t border-gray-100 px-3 py-3">
            <div className={`text-xs text-gray-500 ${isOpen ? 'block' : 'hidden'}`}>
              <div className="mb-1">
                <span className="font-medium">Session:</span>
                <div className="font-mono text-xs break-all">
                  {connectionInfo.sessionId.substring(0, 8)}...
                </div>
              </div>
              <div>
                <span className="font-medium">User:</span>
                <div className="font-mono text-xs">
                  {connectionInfo.userId.startsWith('anonymous_') 
                    ? `Anonymous (${connectionInfo.userId.substring(9)})`
                    : connectionInfo.userId
                  }
                </div>
              </div>
            </div>
            {!isOpen && (
              <div className="w-2 h-2 bg-green-500 rounded-full mx-auto" title="Connected"></div>
            )}
          </div>
        )}

        {/* Bottom section with proper spacing */}
        <div className="border-t border-gray-100 px-3 py-4">
          {isLoggedIn
            ? sidebarButton(
                <>
                  <User size={20} color="#FF9E00" className="shrink-0" />
                  {isOpen && (
                    <>
                      <span className="font-medium whitespace-nowrap">Profile</span>
                      <LogOut size={16} color="#FF9E00" className="ml-auto shrink-0" />
                    </>
                  )}
                </>,
                handleLogout,
                'Sign Out'
              )
            : sidebarButton(
                <>
                  <User size={20} color="#FF9E00" className="shrink-0" />
                  {isOpen && <span className="font-medium whitespace-nowrap">Sign In</span>}
                </>,
                handleLogin,
                'Sign In'
              )}
        </div>
      </div>

      {/* Personalization Modal */}
      <PersonalizationModal
        isOpen={isPersonalizationModalOpen}
        onClose={() => setIsPersonalizationModalOpen(false)}
        onSave={handlePersonalizationSave}
      />
    </>
  );
};

export default Sidebar;