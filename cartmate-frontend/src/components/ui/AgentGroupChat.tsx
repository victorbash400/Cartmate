import React, { useEffect, useState } from 'react';

interface AgentGroupChatProps {
  isVisible: boolean;
  toggleVisibility: () => void;
}

const AgentGroupChat: React.FC<AgentGroupChatProps> = ({ isVisible, toggleVisibility }) => {
  const [isMobile, setIsMobile] = useState(false);

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

  return (
    <>
      {/* Mobile overlay */}
      {isMobile && isVisible && (
        <div 
          className="fixed top-0 left-0 w-full h-full bg-black bg-opacity-20 z-40 transition-opacity duration-300 opacity-100 visible"
          onClick={handleOverlayClick}
        />
      )}
      
      <div className={`bg-white border-none rounded-xl overflow-hidden transition-all duration-300 flex-shrink-0 mr-5 mt-5 mb-5 h-[calc(100vh-40px)] ${
        isVisible ? 'w-[350px] border border-gray-300' : 'w-0 border-0'
      } ${isMobile ? 'fixed top-0 right-0 z-50 w-full h-full m-0 rounded-none transform transition-transform duration-300 ' + (isVisible ? 'translate-x-0' : 'translate-x-full') : ''}`} />
    </>
  );
};

export default AgentGroupChat;