import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Grid3X3,
  Briefcase,
  Users,
  Settings,
  LogOut,
  Bell,
  User,
  ChevronLeft,
  Sparkles
} from 'lucide-react';

const Sidebar = ({ activeTab, setActiveTab, userRole, setUserRole, isOpen, setIsOpen }) => {
  const menuItems = [
    { id: 'dashboard', icon: Grid3X3, label: 'Dashboard' },
    { id: 'career', icon: Briefcase, label: 'Jobs' },
    { id: 'applications', icon: Users, label: 'Candidates' },
  ];

  const toggleSidebar = () => {
    setIsOpen(!isOpen);
  };

  return (
    <motion.div
      initial={false}
      animate={{ 
        width: isOpen ? 240 : 72
      }}
      transition={{ 
        duration: 0.25, 
        ease: [0.4, 0, 0.2, 1]
      }}
      className="fixed left-0 top-0 h-full bg-white border-r border-gray-100 z-50 flex flex-col"
    >
      {/* Header */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-gray-100">
        <motion.div
          className={`flex items-center space-x-3 ${!isOpen ? 'cursor-pointer hover:bg-gray-50 rounded-lg p-2 -m-2 transition-colors' : ''}`}
          animate={{ justifyContent: isOpen ? 'flex-start' : 'center' }}
          onClick={!isOpen ? toggleSidebar : undefined}
          whileHover={!isOpen ? { scale: 1.05 } : {}}
          whileTap={!isOpen ? { scale: 0.95 } : {}}
        >
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <AnimatePresence>
            {isOpen && (
              <motion.span
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                className="font-semibold text-gray-900"
              >
                Workforce
              </motion.span>
            )}
          </AnimatePresence>
        </motion.div>
        
        <AnimatePresence>
          {isOpen && (
            <motion.button
              initial={{ opacity: 0, scale: 0 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0 }}
              onClick={toggleSidebar}
              className="w-6 h-6 flex items-center justify-center text-gray-400 hover:text-gray-600 transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
            </motion.button>
          )}
        </AnimatePresence>
      </div>

      {/* User Section */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="p-4 border-b border-gray-100"
          >
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center">
                <User className="w-4 h-4 text-gray-600" />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">John Smith</p>
                <p className="text-xs text-gray-500 truncate">
                  {userRole === 'hr' ? 'HR Manager' : 'Employee'}
                </p>
              </div>
            </div>
            <select
              value={userRole}
              onChange={(e) => setUserRole(e.target.value)}
              className="w-full mt-3 text-xs border border-gray-200 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="hr">HR Manager</option>
              <option value="employee">Employee</option>
            </select>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-1">
        {menuItems.map((item, index) => (
          <motion.button
            key={item.id}
            onClick={() => setActiveTab(item.id)}
            className={`w-full group relative flex items-center rounded-lg transition-all duration-200 ${
              activeTab === item.id
                ? 'bg-blue-50 text-blue-600'
                : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
            } ${isOpen ? 'px-3 py-2.5' : 'px-2 py-2.5 justify-center'}`}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            <item.icon className={`w-5 h-5 flex-shrink-0 ${
              activeTab === item.id ? 'text-blue-600' : 'text-gray-500'
            }`} />
            
            <AnimatePresence>
              {isOpen && (
                <motion.span
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -10 }}
                  transition={{ duration: 0.15 }}
                  className="ml-3 text-sm font-medium truncate"
                >
                  {item.label}
                </motion.span>
              )}
            </AnimatePresence>

            {/* Active indicator */}
            {activeTab === item.id && (
              <motion.div
                layoutId="activeIndicator"
                className="absolute right-2 w-1.5 h-1.5 bg-blue-600 rounded-full"
                transition={{ type: "spring", stiffness: 400, damping: 30 }}
              />
            )}

            {/* Tooltip for collapsed state */}
            {!isOpen && (
              <div className="absolute left-full ml-2 px-2 py-1 bg-gray-900 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50">
                {item.label}
              </div>
            )}
          </motion.button>
        ))}
      </nav>

      {/* Bottom Section */}
      <div className="p-3 space-y-1 border-t border-gray-100">
        {/* Notifications */}
        <motion.button
          className={`w-full group relative flex items-center rounded-lg transition-all duration-200 text-gray-600 hover:bg-gray-50 hover:text-gray-900 ${
            isOpen ? 'px-3 py-2.5' : 'px-2 py-2.5 justify-center'
          }`}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          <div className="relative">
            <Bell className="w-5 h-5 text-gray-500" />
            <div className="absolute -top-1 -right-1 w-2 h-2 bg-red-500 rounded-full"></div>
          </div>
          
          <AnimatePresence>
            {isOpen && (
              <motion.span
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                transition={{ duration: 0.15 }}
                className="ml-3 text-sm font-medium truncate"
              >
                Notifications
              </motion.span>
            )}
          </AnimatePresence>

          {!isOpen && (
            <div className="absolute left-full ml-2 px-2 py-1 bg-gray-900 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50">
              Notifications
            </div>
          )}
        </motion.button>

        {/* Settings */}
        <motion.button
          className={`w-full group relative flex items-center rounded-lg transition-all duration-200 text-gray-600 hover:bg-gray-50 hover:text-gray-900 ${
            isOpen ? 'px-3 py-2.5' : 'px-2 py-2.5 justify-center'
          }`}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          <Settings className="w-5 h-5 text-gray-500" />
          
          <AnimatePresence>
            {isOpen && (
              <motion.span
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                transition={{ duration: 0.15 }}
                className="ml-3 text-sm font-medium truncate"
              >
                Settings
              </motion.span>
            )}
          </AnimatePresence>

          {!isOpen && (
            <div className="absolute left-full ml-2 px-2 py-1 bg-gray-900 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50">
              Settings
            </div>
          )}
        </motion.button>

        {/* Logout */}
        <motion.button
          className={`w-full group relative flex items-center rounded-lg transition-all duration-200 text-gray-600 hover:bg-red-50 hover:text-red-600 ${
            isOpen ? 'px-3 py-2.5' : 'px-2 py-2.5 justify-center'
          }`}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          <LogOut className="w-5 h-5 text-gray-500 group-hover:text-red-500" />
          
          <AnimatePresence>
            {isOpen && (
              <motion.span
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                transition={{ duration: 0.15 }}
                className="ml-3 text-sm font-medium truncate group-hover:text-red-600"
              >
                Logout
              </motion.span>
            )}
          </AnimatePresence>

          {!isOpen && (
            <div className="absolute left-full ml-2 px-2 py-1 bg-gray-900 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50">
              Logout
            </div>
          )}
        </motion.button>
      </div>
    </motion.div>
  );
};

export default Sidebar;