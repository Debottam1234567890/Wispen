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
      initial={{ y: -600, rotate: -15, opacity: 0 }} /* Falling from sky high */
      animate={{ y: 0, rotate: -2, opacity: 1 }}
      transition={{
        type: "spring",
        stiffness: 180, /* Bouncier */
        damping: 12,    /* Heavy thud */
        mass: 2,        /* Heavy object */
        delay: 1.2      /* Wait for other things */
      }}
      whileHover={{ scale: 1.02, rotate: 0 }}
      whileTap={{ scale: 0.98 }}
      onHoverStart={() => setIsHovered(true)}
      onHoverEnd={() => setIsHovered(false)}
      onClick={onClick}
    >
      <div className={`golden-ticket ${isHovered ? 'glowing' : ''}`}>
        {/* Metal Imperfections/Scratches */}
        <div className="scratch scratch-1"></div>
        <div className="scratch scratch-2"></div>
        <div className="scratch scratch-3"></div>
        <div className="dent dent-1"></div>

        {/* Industrial Corners */}
        <div className="ticket-corner corner-tl"></div>
        <div className="ticket-corner corner-tr"></div>
        <div className="ticket-corner corner-bl"></div>
        <div className="ticket-corner corner-br"></div>

        {/* Border decoration */}
        <div className="ticket-border">
          <svg width="100%" height="100%" preserveAspectRatio="none">
            <rect x="5" y="5" style={{ width: "calc(100% - 10px)", height: "calc(100% - 10px)" }}
              fill="none" stroke="rgba(255,255,255,0.4)" strokeWidth="2" strokeDasharray="4,4" />
          </svg>
        </div>

        {/* Content */}
        <div className="ticket-content">
          <div className="ticket-header">
            <div className="ornament">★</div>
            <div className="ticket-title">OFFICIAL PASS</div>
            <div className="ornament">★</div>
          </div>

          <div className="ticket-main">
            <div className="willy-wonka-text">GET STARTED</div>
          </div>

          <div className="ticket-footer">
            <div className="ticket-tagline">Access Granted · Level 1</div>
            <div className="ticket-number">ID: {Math.floor(Math.random() * 10000).toString().padStart(5, '0')}</div>
          </div>
        </div>

        {/* Sheen effect */}
        <motion.div
          className="shimmer-overlay"
          animate={{
            x: isHovered ? ['-100%', '100%'] : '-100%',
          }}
          transition={{
            duration: 0.8,
            ease: 'linear',
          }}
        />
      </div>
    </motion.div>
  );
}
