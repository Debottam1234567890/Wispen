import { useState } from 'react';
import { motion } from 'framer-motion';
import type { FloatingButtonProps } from '../types';
import './FloatingButton.css';

export default function FloatingButton({ 
  text, 
  icon, 
  gradient, 
  rotation, 
  onClick 
}: FloatingButtonProps) {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <motion.div
      className="floating-button-container"
      style={{ transform: `rotate(${rotation}deg)` }}
      whileHover={{ y: -10, scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      onHoverStart={() => setIsHovered(true)}
      onHoverEnd={() => setIsHovered(false)}
      onClick={onClick}
    >
      <div 
        className="floating-button"
        style={{ background: gradient }}
      >
        <span className="button-icon">{icon}</span>
        <span className="button-text">{text}</span>
      </div>

      {/* Scribbled Shadow */}
      <svg 
        className="button-shadow" 
        width="100%" 
        height="20" 
        style={{ 
          filter: isHovered ? 'blur(4px)' : 'blur(2px)',
          opacity: isHovered ? 0.6 : 0.3
        }}
      >
        <path 
          d="M 10 10 Q 50 8 90 10 Q 130 12 170 10" 
          stroke="var(--ink-shadow)" 
          strokeWidth="3" 
          fill="none"
          strokeLinecap="round"
        />
      </svg>

      {/* Hover Arrow */}
      {isHovered && (
        <motion.div
          className="hover-arrow"
          initial={{ opacity: 0, y: -10 }}
          animate={{ 
            opacity: 1, 
            y: [-15, -20, -15],
          }}
          transition={{
            y: {
              duration: 0.6,
              repeat: Infinity,
              ease: "easeInOut"
            }
          }}
        >
          <svg width="30" height="30" viewBox="0 0 30 30">
            <path 
              d="M 5 20 L 15 5 L 25 20" 
              stroke="var(--ink-shadow)" 
              strokeWidth="3" 
              fill="none"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </motion.div>
      )}

      {/* Sparkle Particles on Hover */}
      {isHovered && (
        <>
          {[...Array(5)].map((_, i) => (
            <motion.div
              key={i}
              className="sparkle-particle"
              initial={{ 
                opacity: 0, 
                scale: 0,
                x: 0,
                y: 0
              }}
              animate={{ 
                opacity: [0, 1, 0], 
                scale: [0, 1, 0],
                x: Math.cos(i * 72 * Math.PI / 180) * 50,
                y: Math.sin(i * 72 * Math.PI / 180) * 50
              }}
              transition={{ 
                duration: 0.6,
                repeat: Infinity,
                delay: i * 0.1
              }}
            >
              ✨
            </motion.div>
          ))}
        </>
      )}
    </motion.div>
  );
}