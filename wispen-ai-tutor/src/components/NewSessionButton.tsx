import { motion } from 'framer-motion';
import './NewSessionButton.css';

interface NewSessionButtonProps {
  onClick?: () => void;
}

export default function NewSessionButton({ onClick }: NewSessionButtonProps) {
  return (
    <motion.button
      className="new-session-btn"
      onClick={onClick}
      whileHover={{ scale: 1.05, rotate: -1 }}
      whileTap={{ scale: 0.95 }}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.5 }}
    >
      <div className="btn-content">
        <span className="plus-icon">+</span>
        <span className="btn-text">NEW SESSION</span>
      </div>
      <div className="btn-scribble"></div>
    </motion.button>
  );
}