import React, { useEffect, useState } from 'react';
import { CircleChevronLeft, CircleChevronRight, MessageCircle, User, LogOut, PersonStanding } from 'lucide-react';
import './Sidebar.css';

interface SidebarProps {
  isOpen: boolean;
  toggleSidebar: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ isOpen, toggleSidebar }) => {
  const [isMobile, setIsMobile] = useState(false);
  const [isLoggedIn, setIsLoggedIn] = useState(false);

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

  const handleNewSession = () => {
    // Add new session logic here
    console.log('New session started');
  };

  const handleLogin = () => {
    // Placeholder for login functionality
    setIsLoggedIn(true);
    console.log('User logged in');
  };

  const handleLogout = () => {
    // Placeholder for logout functionality
    setIsLoggedIn(false);
    console.log('User logged out');
  };

  return (
    <>
      {/* Mobile overlay */}
      {isMobile && (
        <div 
          className={`sidebar-overlay ${isOpen ? 'active' : ''}`}
          onClick={handleOverlayClick}
        />
      )}
      
      <div className={`sidebar ${isOpen ? 'open' : 'closed'}`}>
        <h2>CartMate</h2>
        
        {/* Personalization Section */}
        <div className="personalization-section">
          <button className="personalization-button" title="Personalization">
            <PersonStanding size={20} color="#FF9E00" />
            {isOpen && <span className="button-text">Personalization</span>}
          </button>
        </div>
        
        <button className="toggle-button" onClick={toggleSidebar}>
          {isOpen ? <CircleChevronLeft size={20} color="#FF9E00" /> : <CircleChevronRight size={20} color="#FF9E00" />}
        </button>
        <button className="new-chat-button" onClick={handleNewSession} title="New Chat">
          <MessageCircle size={20} color="#FF9E00" />
          {isOpen && <span className="button-text">New Chat</span>}
        </button>
        
        {/* Login/Logout Button at the bottom */}
        <div className="login-section">
          {isLoggedIn ? (
            <button className="auth-button" onClick={handleLogout} title="Sign Out">
              <User size={20} color="#FF9E00" />
              {isOpen && <span className="button-text">Profile</span>}
              <LogOut size={16} color="#FF9E00" className="logout-icon" />
            </button>
          ) : (
            <button className="auth-button" onClick={handleLogin} title="Sign In">
              <User size={20} color="#FF9E00" />
              {isOpen && <span className="button-text">Sign In</span>}
            </button>
          )}
        </div>
      </div>
    </>
  );
};

export default Sidebar;