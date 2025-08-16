import React, { useState } from 'react';
import { motion } from 'framer-motion';
import Sidebar from './Sidebar';

const Layout = ({ children, activeTab, setActiveTab, userRole, setUserRole }) => {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <div className="min-h-screen clean-bg">
      <div className="flex">
        <Sidebar 
          activeTab={activeTab} 
          setActiveTab={setActiveTab}
          userRole={userRole}
          setUserRole={setUserRole}
          isOpen={sidebarOpen}
          setIsOpen={setSidebarOpen}
        />
        <motion.main 
          className="flex-1 main-content"
          style={{ 
            marginLeft: sidebarOpen ? '240px' : '72px' 
          }}
        >
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="p-8 pt-20"
          >
            <div className="max-w-7xl mx-auto">
              {children}
            </div>
          </motion.div>
        </motion.main>
      </div>
    </div>
  );
};

export default Layout;