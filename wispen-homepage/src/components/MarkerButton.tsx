import { useState } from 'react';
import { motion } from 'framer-motion';
import './MarkerButton.css';

interface MarkerButtonProps {
  onClick?: () => void;
}

export default function MarkerButton({ onClick }: MarkerButtonProps) {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <motion.div
      className="marker-button-wrapper"
      whileHover={{ scale: 1.05, rotate: -1 }}
      whileTap={{ scale: 0.95 }}
      onHoverStart={() => setIsHovered(true)}
      onHoverEnd={() => setIsHovered(false)}
      onClick={onClick}
    >
      <svg 
        className="marker-button-svg" 
        viewBox="0 0 400 150" 
        width="400" 
        height="150"
      >
        <defs>
          {/* Marker texture filter */}
          <filter id="markerTexture">
            <feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="4" result="noise" />
            <feDisplacementMap in="SourceGraphic" in2="noise" scale="3" />
          </filter>

          {/* Glow filter */}
          <filter id="markerGlow">
            <feGaussianBlur stdDeviation="4" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>

        {/* Background rectangle with hand-drawn effect */}
        <motion.path
          d="M 25 30 
             L 375 25 
             Q 380 25 380 30
             L 385 115
             Q 385 120 380 120
             L 30 125
             Q 25 125 25 120
             Z"
          fill="#FF6B6B"
          stroke="#B83232"
          strokeWidth="4"
          strokeLinecap="round"
          filter="url(#markerTexture)"
          animate={isHovered ? {
            fill: ['#FF6B6B', '#FF8787', '#FF6B6B'],
          } : {}}
          transition={{ duration: 0.5 }}
        />

        {/* Marker streaks for texture */}
        <g opacity="0.3">
          <line x1="40" y1="45" x2="360" y2="43" stroke="#B83232" strokeWidth="2" />
          <line x1="40" y1="60" x2="355" y2="58" stroke="#B83232" strokeWidth="1.5" />
          <line x1="45" y1="95" x2="350" y2="93" stroke="#B83232" strokeWidth="2" />
          <line x1="40" y1="110" x2="360" y2="108" stroke="#B83232" strokeWidth="1.5" />
        </g>

        {/* Hand-drawn border effect */}
        <motion.path
          d="M 25 30 
             L 375 25 
             L 385 115
             L 30 125
             Z"
          fill="none"
          stroke="#4A0E0E"
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
          animate={isHovered ? {
            strokeWidth: [3, 4, 3],
          } : {}}
          transition={{ duration: 0.5 }}
        />

        {/* Main text */}
        <text
          x="200"
          y="65"
          fontFamily="Permanent Marker, cursive"
          fontSize="28"
          fontWeight="bold"
          fill="#FFFFFF"
          textAnchor="middle"
          filter={isHovered ? "url(#markerGlow)" : "none"}
        >
          Check Your
        </text>

        <text
          x="200"
          y="100"
          fontFamily="Permanent Marker, cursive"
          fontSize="36"
          fontWeight="bold"
          fill="#FFFFFF"
          textAnchor="middle"
          filter={isHovered ? "url(#markerGlow)" : "none"}
        >
          Progress
        </text>

        {/* Decorative checkmark */}
        <motion.path
          d="M 50 75 L 60 85 L 75 65"
          stroke="#FFFFFF"
          strokeWidth="5"
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
          initial={{ pathLength: 0 }}
          animate={isHovered ? { pathLength: 1 } : { pathLength: 0 }}
          transition={{ duration: 0.5 }}
        />

        {/* Decorative arrow */}
        <motion.path
          d="M 325 75 L 345 75 L 340 70 M 345 75 L 340 80"
          stroke="#FFFFFF"
          strokeWidth="5"
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
          animate={isHovered ? {
            x: [0, 5, 0],
          } : {}}
          transition={{ duration: 0.6, repeat: isHovered ? Infinity : 0 }}
        />

        {/* Ink drips */}
        <g className="ink-drips" opacity={isHovered ? "0.6" : "0"}>
          <motion.ellipse
            cx="100"
            cy="125"
            rx="4"
            ry="8"
            fill="#B83232"
            animate={isHovered ? {
              cy: [125, 135],
              opacity: [0.6, 0],
            } : {}}
            transition={{ duration: 1.5, repeat: Infinity, delay: 0 }}
          />
          <motion.ellipse
            cx="300"
            cy="125"
            rx="3"
            ry="7"
            fill="#B83232"
            animate={isHovered ? {
              cy: [125, 135],
              opacity: [0.6, 0],
            } : {}}
            transition={{ duration: 1.5, repeat: Infinity, delay: 0.5 }}
          />
        </g>
      </svg>

      {/* Marker cap icon */}
      <motion.div
        className="marker-cap"
        animate={isHovered ? {
          rotate: [0, -10, 0],
          x: [-5, 5, -5],
        } : {}}
        transition={{ duration: 1.5, repeat: isHovered ? Infinity : 0 }}
      >
        <svg width="30" height="40" viewBox="0 0 30 40">
          <rect x="5" y="0" width="20" height="35" fill="#333" rx="3" />
          <rect x="8" y="5" width="14" height="5" fill="#666" />
          <ellipse cx="15" cy="35" rx="10" ry="5" fill="#222" />
        </svg>
      </motion.div>

      {/* Scribble particles */}
      {isHovered && (
        <div className="scribble-particles">
          {[...Array(6)].map((_, i) => (
            <motion.div
              key={i}
              className="scribble"
              style={{
                left: `${20 + Math.random() * 60}%`,
                top: `${20 + Math.random() * 60}%`,
              }}
              initial={{ opacity: 0, scale: 0, rotate: 0 }}
              animate={{
                opacity: [0, 1, 0],
                scale: [0, 1.5, 0],
                rotate: [0, 360],
              }}
              transition={{
                duration: 1.5,
                repeat: Infinity,
                delay: i * 0.2,
              }}
            >
              ╱
            </motion.div>
          ))}
        </div>
      )}
    </motion.div>
  );
}
