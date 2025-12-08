import { useState } from 'react';
import { motion } from 'framer-motion';
import type { StickyNoteProps } from '../types';
import './StickyNote.css';

export default function StickyNote({ 
  content, 
  initialX, 
  initialY, 
  driftSpeed, 
  rotation 
}: StickyNoteProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <motion.div
      className={`sticky-note ${isExpanded ? 'expanded' : ''}`}
      initial={{ x: initialX, y: initialY, rotate: rotation }}
      animate={{
        x: [initialX, initialX + 30, initialX - 20, initialX],
        y: [initialY, initialY - 20, initialY + 10, initialY],
        rotate: [rotation, rotation + 2, rotation - 2, rotation]
      }}
      transition={{
        duration: driftSpeed,
        repeat: Infinity,
        ease: "easeInOut"
      }}
      onClick={() => setIsExpanded(!isExpanded)}
      whileHover={{ scale: 1.05, zIndex: 100 }}
      whileTap={{ scale: 0.95 }}
    >
      <div className="sticky-note-content">
        {!isExpanded ? (
          <div className="sticky-note-doodle">
            <svg width="60" height="60" viewBox="0 0 60 60">
              <circle cx="20" cy="20" r="3" fill="var(--ink-shadow)" opacity="0.6" />
              <circle cx="40" cy="25" r="2" fill="var(--ink-shadow)" opacity="0.6" />
              <path d="M 10 35 Q 20 30 30 35" stroke="var(--ink-shadow)" strokeWidth="2" fill="none" opacity="0.5" />
              <text x="15" y="50" fontSize="14" fill="var(--ink-shadow)" opacity="0.7">📝</text>
            </svg>
          </div>
        ) : (
          <div className="sticky-note-text">
            <p className="handwritten-text">{content}</p>
          </div>
        )}
      </div>
    </motion.div>
  );
}