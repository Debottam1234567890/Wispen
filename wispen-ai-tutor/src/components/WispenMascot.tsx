import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import type { WispenMascotProps } from '../types';
import './WispenMascot.css';

const PHANTOM_WORDS = ['Learn', 'Create', 'Wonder'];

export default function WispenMascot({ onGlassesClick, onPenWrite }: WispenMascotProps) {
  const [currentWord, setCurrentWord] = useState('');
  const [showWord, setShowWord] = useState(false);
  const [glassesOff, setGlassesOff] = useState(false);

  useEffect(() => {
    const interval = setInterval(() => {
      const randomWord = PHANTOM_WORDS[Math.floor(Math.random() * PHANTOM_WORDS.length)];
      setCurrentWord(randomWord);
      setShowWord(true);
      onPenWrite?.(randomWord);

      setTimeout(() => {
        setShowWord(false);
      }, 3000);
    }, 8000);

    return () => clearInterval(interval);
  }, [onPenWrite]);

  const handleGlassesClick = () => {
    setGlassesOff(true);
    onGlassesClick?.();
    
    setTimeout(() => {
      setGlassesOff(false);
    }, 2000);
  };

  return (
    <div className="wispen-mascot-container">
      {/* Speech Bubble from Design */}
      <motion.div 
        className="speech-bubble"
        initial={{ opacity: 0, scale: 0.8, x: -50 }}
        animate={{ opacity: 1, scale: 1, x: 0 }}
        transition={{ delay: 1, duration: 0.8, type: "spring" }}
      >
        <div className="bubble-text">
          Ever felt tired and stressed about school work?
        </div>
        <div className="bubble-tail"></div>
      </motion.div>

      {/* Constellation Halo */}
      <motion.div 
        className="constellation-halo"
        animate={{ rotate: 360 }}
        transition={{ duration: 60, repeat: Infinity, ease: "linear" }}
      >
        <svg width="400" height="400" viewBox="0 0 400 400">
          <circle cx="200" cy="80" r="3" fill="var(--vapor-cyan)" opacity="0.6" />
          <circle cx="320" cy="200" r="3" fill="var(--mystic-lavender)" opacity="0.6" />
          <circle cx="200" cy="320" r="3" fill="var(--dream-pink)" opacity="0.6" />
          <circle cx="80" cy="200" r="3" fill="var(--vapor-cyan)" opacity="0.6" />
          <line x1="200" y1="80" x2="320" y2="200" stroke="var(--mystic-lavender)" strokeWidth="1" opacity="0.3" />
          <line x1="320" y1="200" x2="200" y2="320" stroke="var(--dream-pink)" strokeWidth="1" opacity="0.3" />
          <line x1="200" y1="320" x2="80" y2="200" stroke="var(--vapor-cyan)" strokeWidth="1" opacity="0.3" />
          <line x1="80" y1="200" x2="200" y2="80" stroke="var(--mystic-lavender)" strokeWidth="1" opacity="0.3" />
        </svg>
      </motion.div>

      {/* WISPEN Mascot */}
      <motion.div
        className="wispen-mascot pulse-glow"
        animate={{
          y: [0, -15, 0],
        }}
        transition={{
          duration: 2,
          repeat: Infinity,
          ease: "easeInOut"
        }}
      >
        <img 
          src="/gemini-image-2_Cute_2D_Pixar-style_magical_glowing_wisp_wizard_mascot_tiny_floating_upper_body_-0.png" 
          alt="WISPEN - Your AI Tutor Mascot"
          className="mascot-image"
        />
        
        {/* Clickable Glasses Overlay */}
        {!glassesOff && (
          <div 
            className="glasses-clickable"
            onClick={handleGlassesClick}
            role="button"
            tabIndex={0}
            aria-label="Click WISPEN's glasses"
          />
        )}

        {/* Falling Glasses Animation */}
        {glassesOff && (
          <motion.div
            className="falling-glasses"
            initial={{ y: 0, rotate: 0, opacity: 1 }}
            animate={{ 
              y: 500, 
              rotate: 720,
              opacity: 0
            }}
            transition={{ 
              duration: 2,
              ease: "easeIn"
            }}
          >
            👓
          </motion.div>
        )}
      </motion.div>

      {/* Glowing Pen with Trail */}
      <motion.div
        className="glowing-pen"
        animate={{
          rotate: [0, 10, -10, 0],
          x: [0, 5, -5, 0]
        }}
        transition={{
          duration: 3,
          repeat: Infinity,
          ease: "easeInOut"
        }}
      >
        <svg width="60" height="60" viewBox="0 0 60 60">
          <defs>
            <filter id="glow">
              <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
              <feMerge>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
          </defs>
          <path 
            d="M10 50 L20 10 L25 15 L15 55 Z" 
            fill="var(--vapor-cyan)" 
            filter="url(#glow)"
            opacity="0.9"
          />
          <circle cx="22" cy="12" r="8" fill="var(--vapor-cyan)" filter="url(#glow)" opacity="0.6" />
        </svg>
      </motion.div>

      {/* Phantom Words */}
      {showWord && (
        <motion.div
          className="phantom-word"
          initial={{ opacity: 0, y: 0, scale: 0.9 }}
          animate={{ opacity: [0, 1, 1, 0], y: -50, scale: 1 }}
          transition={{ duration: 3 }}
        >
          {currentWord.split('').map((ch, i) => (
            <motion.span
              key={`${ch}-${i}`}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: i * 0.08 }}
            >
              {ch}
            </motion.span>
          ))}
        </motion.div>
      )}
    </div>
  );
}
