import { motion } from 'framer-motion';
import './BackgroundDoodles.css';

export default function BackgroundDoodles() {
  const pencils = [
    { id: 1, x: '10%', y: '20%', rotation: 45, duration: 15 },
    { id: 2, x: '80%', y: '30%', rotation: -30, duration: 18 },
    { id: 3, x: '15%', y: '70%', rotation: 120, duration: 20 },
    { id: 4, x: '85%', y: '80%', rotation: -60, duration: 16 }
  ];

  return (
    <div className="background-doodles">
      {/* Floating Pencils */}
      {pencils.map(pencil => (
        <motion.div
          key={pencil.id}
          className="floating-pencil"
          style={{ left: pencil.x, top: pencil.y }}
          animate={{
            y: [0, -20, 0],
            rotate: [pencil.rotation, pencil.rotation + 15, pencil.rotation],
            x: [0, 10, 0]
          }}
          transition={{
            duration: pencil.duration,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        >
          <svg width="80" height="20" viewBox="0 0 80 20">
            <rect x="0" y="7" width="60" height="6" fill="var(--mystic-lavender)" opacity="0.6" />
            <polygon points="60,7 70,10 60,13" fill="var(--ink-shadow)" opacity="0.7" />
            <rect x="5" y="8" width="50" height="4" fill="var(--chalk-white)" opacity="0.3" />
          </svg>
        </motion.div>
      ))}

      {/* Geometric Shapes */}
      <motion.div
        className="geometric-shape triangle"
        animate={{ rotate: 360 }}
        transition={{ duration: 40, repeat: Infinity, ease: "linear" }}
      >
        <svg width="60" height="60" viewBox="0 0 60 60">
          <polygon 
            points="30,10 50,50 10,50" 
            fill="none" 
            stroke="var(--vapor-cyan)" 
            strokeWidth="2"
            opacity="0.3"
          />
        </svg>
      </motion.div>

      <motion.div
        className="geometric-shape spiral"
        animate={{ rotate: -360 }}
        transition={{ duration: 50, repeat: Infinity, ease: "linear" }}
      >
        <svg width="80" height="80" viewBox="0 0 80 80">
          <path 
            d="M 40 40 Q 40 20 60 20 Q 80 20 80 40 Q 80 60 60 60 Q 40 60 40 40" 
            fill="none" 
            stroke="var(--dream-pink)" 
            strokeWidth="2"
            opacity="0.3"
          />
        </svg>
      </motion.div>
    </div>
  );
}