import { motion } from 'framer-motion';
import './Header.css';

export default function Header() {
  return (
    <header className="header">
      {/* Corner Doodles */}
      <motion.div 
        className="corner-doodle bookmark"
        animate={{ rotate: [0, 5, 0, -5, 0] }}
        transition={{ duration: 4, repeat: Infinity }}
      >
        <svg width="60" height="80" viewBox="0 0 60 80">
          <path 
            d="M 10 10 L 50 10 L 50 70 L 30 55 L 10 70 Z" 
            fill="var(--dream-pink)" 
            stroke="var(--ink-shadow)" 
            strokeWidth="2"
            opacity="0.8"
          />
          <text x="15" y="35" fontSize="10" fill="var(--chalk-white)" fontFamily="var(--font-ui)">
            Beta
          </text>
          <text x="15" y="50" fontSize="10" fill="var(--chalk-white)" fontFamily="var(--font-ui)">
            v1.0
          </text>
        </svg>
      </motion.div>

      <motion.div 
        className="corner-doodle eraser"
        animate={{ rotate: [0, -10, 10, 0] }}
        transition={{ duration: 5, repeat: Infinity }}
      >
        <svg width="70" height="40" viewBox="0 0 70 40">
          <rect 
            x="10" 
            y="10" 
            width="50" 
            height="20" 
            fill="var(--mystic-lavender)" 
            stroke="var(--ink-shadow)" 
            strokeWidth="2"
            opacity="0.8"
            rx="3"
          />
          <rect x="15" y="15" width="15" height="10" fill="var(--chalk-white)" opacity="0.5" />
        </svg>
      </motion.div>

      {/* Title */}
      <motion.h1 
        className="title-text wobble"
        initial={{ opacity: 0, y: -50 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 1, delay: 0.2 }}
      >
        WISPEN
      </motion.h1>

      {/* Tagline */}
      <motion.p 
        className="tagline-text fade-in"
        initial={{ opacity: 0 }}
        animate={{ opacity: 0.8 }}
        transition={{ duration: 2, delay: 0.8 }}
      >
        Your Academic Companion
      </motion.p>

      {/* Ink Splatters */}
      <motion.div
        className="ink-splatter splatter-1"
        animate={{ scale: [1, 1.1, 1], opacity: [0.3, 0.5, 0.3] }}
        transition={{ duration: 3, repeat: Infinity }}
      >
        <svg width="30" height="30" viewBox="0 0 30 30">
          <circle cx="15" cy="15" r="8" fill="var(--vapor-cyan)" opacity="0.3" />
          <circle cx="10" cy="10" r="3" fill="var(--vapor-cyan)" opacity="0.4" />
          <circle cx="20" cy="18" r="4" fill="var(--vapor-cyan)" opacity="0.3" />
        </svg>
      </motion.div>
    </header>
  );
}