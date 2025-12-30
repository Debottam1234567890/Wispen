import { BrowserRouter as Router, Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import Home from './components/Home';
import SignUpPage from './components/SignUpPage';
import LogInPage from './components/LogInPage';
import Dashboard from './components/dashboard/Dashboard';
import ChatInterface from './components/chat/ChatInterface';
import HowItWorks from './components/HowItWorks';
import TimeTracker from './components/TimeTracker';
import './App.css';

// Animated Route Wrapper
const AnimatedRoutes = () => {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <AnimatePresence mode="wait">
      <Routes>
        <Route
          path="/"
          element={
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              style={{ width: '100%', height: '100%' }}
            >
              <Home />
            </motion.div>
          }
        />
        <Route
          path="/signup"
          element={
            <motion.div
              initial={{ x: '100%', opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: '-100%', opacity: 0 }}
              transition={{ type: 'spring', damping: 20 }}
              style={{ width: '100%', height: '100%' }}
            >
              <SignUpPage
                onSwitchToLogin={() => navigate('/login')}
                onEnterFactory={(uid: string) => navigate(`/${uid}/dashboard`)}
              />
            </motion.div>
          }
        />
        <Route
          path="/login"
          element={
            <motion.div
              initial={{ x: '-100%', opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: '100%', opacity: 0 }}
              transition={{ type: 'spring', damping: 20 }}
              style={{ width: '100%', height: '100%' }}
            >
              <LogInPage
                onSwitchToSignUp={() => navigate('/signup')}
                onEnterFactory={(uid: string) => navigate(`/${uid}/dashboard`)}
              />
            </motion.div>
          }
        />
        <Route
          path="/how-it-works"
          element={
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 1.1 }}
              style={{ width: '100%', height: '100%' }}
            >
              <HowItWorks />
            </motion.div>
          }
        />
        <Route
          path="/:userId/dashboard"
          element={
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 1.05 }}
              style={{ width: '100%', height: '100%' }}
            >
              <Dashboard
                onEnterChat={(sessionId) => navigate(`/${location.pathname.split('/')[1]}/chat?session_id=${sessionId}`)}
                onExit={() => navigate('/')}
              />
            </motion.div>
          }
        />
        <Route
          path="/:userId/chat"
          element={
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              style={{ width: '100%', height: '100%' }}
            >
              <ChatInterface />
            </motion.div>
          }
        />
      </Routes>
    </AnimatePresence>
  );
};

function App() {
  return (
    <Router>
      <TimeTracker />
      <AnimatedRoutes />
    </Router>
  );
}

export default App;
