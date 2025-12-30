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
        <div className="sticky-note-text">
          <p className="handwritten-text">{content}</p>
        </div>
      </div>
    </motion.div>
  );
}
