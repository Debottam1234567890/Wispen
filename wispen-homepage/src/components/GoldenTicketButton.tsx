import { useState } from 'react';
import { motion } from 'framer-motion';
import './GoldenTicketButton.css';

interface GoldenTicketButtonProps {
  onClick?: () => void;
}

export default function GoldenTicketButton({ onClick }: GoldenTicketButtonProps) {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <motion.div
      className="golden-ticket-wrapper"
      whileHover={{ scale: 1.05, rotate: 2 }}
      whileTap={{ scale: 0.95 }}
      onHoverStart={() => setIsHovered(true)}
      onHoverEnd={() => setIsHovered(false)}
      onClick={onClick}
    >
      <div className={`golden-ticket ${isHovered ? 'glowing' : ''}`}>
        {/* Decorative corners */}
        <div className="ticket-corner corner-tl"></div>
        <div className="ticket-corner corner-tr"></div>
        <div className="ticket-corner corner-bl"></div>
        <div className="ticket-corner corner-br"></div>

        {/* Ornate border */}
        <div className="ticket-border">
          <svg width="100%" height="100%" preserveAspectRatio="none">
            <rect x="5" y="5" width="calc(100% - 10px)" height="calc(100% - 10px)" 
                  fill="none" stroke="#8B4513" strokeWidth="2" strokeDasharray="5,3" />
            <rect x="10" y="10" width="calc(100% - 20px)" height="calc(100% - 20px)" 
                  fill="none" stroke="#DAA520" strokeWidth="1" />
          </svg>
        </div>

        {/* Ticket content */}
        <div className="ticket-content">
          <div className="ticket-header">
            <div className="ornament">✦</div>
            <div className="ticket-title">ADMIT ONE</div>
            <div className="ornament">✦</div>
          </div>

          <div className="ticket-main">
            <div className="willy-wonka-text">Getting Started</div>
            <div className="chocolate-decoration">
              <span>🍫</span>
              <span>🍬</span>
              <span>🍫</span>
            </div>
          </div>

          <div className="ticket-footer">
            <div className="ticket-tagline">Begin Your Learning Adventure</div>
            <div className="ticket-number">№ {Math.floor(Math.random() * 10000).toString().padStart(5, '0')}</div>
          </div>
        </div>

        {/* Shimmer effect */}
        <motion.div
          className="shimmer-overlay"
          animate={{
            x: isHovered ? ['-100%', '100%'] : '-100%',
          }}
          transition={{
            duration: 1.5,
            repeat: isHovered ? Infinity : 0,
            ease: 'linear',
          }}
        />

        {/* Golden sparkles */}
        {isHovered && (
          <>
            {[...Array(8)].map((_, i) => (
              <motion.div
                key={i}
                className="golden-sparkle"
                style={{
                  left: `${Math.random() * 100}%`,
                  top: `${Math.random() * 100}%`,
                }}
                initial={{ opacity: 0, scale: 0 }}
                animate={{
                  opacity: [0, 1, 0],
                  scale: [0, 1.5, 0],
                }}
                transition={{
                  duration: 1.5,
                  repeat: Infinity,
                  delay: i * 0.2,
                }}
              >
                ✨
              </motion.div>
            ))}
          </>
        )}
      </div>
    </motion.div>
  );
}
