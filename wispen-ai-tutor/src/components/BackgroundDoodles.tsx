import { motion } from 'framer-motion';
import './BackgroundDoodles.css';

export default function BackgroundDoodles() {
  const pencils = [
    { id: 1, x: '10%', y: '20%', rotation: 45, duration: 15 },
    { id: 2, x: '80%', y: '30%', rotation: -30, duration: 18 },
    { id: 3, x: '15%', y: '70%', rotation: 120, duration: 20 },
    { id: 4, x: '85%', y: '80%', rotation: -60, duration: 16 }
  ];

  const shootingPencils = [
    { id: 'sp-1', y: '18%', duration: 20 },
    { id: 'sp-2', y: '62%', duration: 24 },
  ];

  const scrolls = [
    { id: 'sc-1', x: '12%', y: '10%', duration: 30, rotate: 10 },
    { id: 'sc-2', x: '78%', y: '75%', duration: 26, rotate: -8 },
  ];

  const erasers = [
    { id: 'er-1', x: '6%', y: '45%', duration: 22 },
    { id: 'er-2', x: '90%', y: '20%', duration: 28 },
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

      {/* Big Scrolls */}
      {scrolls.map(sc => (
        <motion.div
          key={sc.id}
          className="background-scroll"
          style={{ left: sc.x, top: sc.y }}
          animate={{ rotate: [sc.rotate, sc.rotate + 6, sc.rotate] }}
          transition={{ duration: sc.duration, repeat: Infinity, ease: 'easeInOut' }}
        >
          <svg width="140" height="70" viewBox="0 0 140 70">
            <rect x="20" y="15" width="100" height="40" fill="#FFF5CC" stroke="var(--ink-shadow)" strokeWidth="2" rx="8" />
            <circle cx="20" cy="35" r="12" fill="#FFE6A3" stroke="var(--ink-shadow)" strokeWidth="2" />
            <circle cx="120" cy="35" r="12" fill="#FFE6A3" stroke="var(--ink-shadow)" strokeWidth="2" />
            <rect x="22" y="25" width="96" height="20" fill="#FFF9D6" opacity="0.8" />
            <line x1="60" y1="15" x2="60" y2="55" stroke="#FF8EC6" strokeWidth="3" opacity="0.6" />
          </svg>
        </motion.div>
      ))}

      {/* Rotating Erasers */}
      {erasers.map(er => (
        <motion.div
          key={er.id}
          className="background-eraser"
          style={{ left: er.x, top: er.y }}
          animate={{ rotate: [0, 360] }}
          transition={{ duration: er.duration, repeat: Infinity, ease: 'linear' }}
        >
          <svg width="90" height="50" viewBox="0 0 90 50">
            <rect x="10" y="10" width="70" height="30" rx="6" fill="#B49FCC" stroke="var(--ink-shadow)" strokeWidth="2" />
            <rect x="50" y="10" width="30" height="30" rx="6" fill="#F4F1E8" opacity="0.8" />
          </svg>
        </motion.div>
      ))}

      {/* Shooting Pencils */}
      {shootingPencils.map(sp => (
        <motion.div
          key={sp.id}
          className="shooting-pencil"
          style={{ top: sp.y, left: '-10%' }}
          animate={{ x: ['-10%', '110%'] }}
          transition={{ duration: sp.duration, repeat: Infinity, ease: 'linear' }}
        >
          <svg width="120" height="24" viewBox="0 0 120 24">
            <rect x="0" y="8" width="90" height="8" fill="var(--vapor-cyan)" opacity="0.5" />
            <polygon points="90,8 110,12 90,16" fill="var(--ink-shadow)" opacity="0.6" />
            <rect x="8" y="9" width="74" height="6" fill="#F4F1E8" opacity="0.4" />
          </svg>
        </motion.div>
      ))}
    </div>
  );
}
