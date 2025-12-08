import { motion } from 'framer-motion';
import './SegmentedMascot.css';

interface SegmentedPart {
  id: string;
  type: 'head' | 'glasses' | 'body' | 'arm-left' | 'arm-right' | 'pen' | 'cloud' | 'star' | 'heart' | 'book';
  x: number;
  y: number;
  rotation: number;
  size: number;
  delay: number;
}

const segments: SegmentedPart[] = [
  { id: 'head-1', type: 'head', x: 15, y: 10, rotation: -8, size: 120, delay: 0 },
  { id: 'glasses-1', type: 'glasses', x: 85, y: 15, rotation: 12, size: 100, delay: 0.2 },
  { id: 'body-1', type: 'body', x: 20, y: 70, rotation: -5, size: 110, delay: 0.4 },
  { id: 'arm-left-1', type: 'arm-left', x: 10, y: 45, rotation: 25, size: 90, delay: 0.6 },
  { id: 'arm-right-1', type: 'arm-right', x: 78, y: 55, rotation: -15, size: 95, delay: 0.8 },
  { id: 'pen-1', type: 'pen', x: 88, y: 78, rotation: 45, size: 80, delay: 1.0 },
  { id: 'cloud-1', type: 'cloud', x: 50, y: 8, rotation: -3, size: 70, delay: 1.2 },
  { id: 'star-1', type: 'star', x: 5, y: 85, rotation: 18, size: 60, delay: 1.4 },
  { id: 'heart-1', type: 'heart', x: 75, y: 35, rotation: -20, size: 65, delay: 1.6 },
  { id: 'book-1', type: 'book', x: 40, y: 88, rotation: 8, size: 75, delay: 1.8 },
  { id: 'head-2', type: 'head', x: 92, y: 88, rotation: 15, size: 85, delay: 2.0 },
  { id: 'cloud-2', type: 'cloud', x: 30, y: 30, rotation: -12, size: 55, delay: 2.2 },
];

const SegmentContent = ({ type }: { type: string }) => {
  const gradients = {
    primary: 'linear-gradient(135deg, #7DF9FF, #B49FCC)',
    secondary: 'linear-gradient(135deg, #FF8EC6, #B49FCC)',
    tertiary: 'linear-gradient(135deg, #7DF9FF, #FF8EC6)',
  };

  switch (type) {
    case 'head':
      return (
        <div className="segment-head" style={{ background: gradients.primary }}>
          <div className="vapor-swirl"></div>
          <div className="face-features">
            <div className="eye left"></div>
            <div className="eye right"></div>
            <div className="smile-curve"></div>
          </div>
        </div>
      );
    
    case 'glasses':
      return (
        <div className="segment-glasses">
          <svg viewBox="0 0 100 40" width="100%" height="100%">
            <circle cx="25" cy="20" r="15" stroke="#4A4A5E" strokeWidth="3" fill="rgba(255,255,255,0.3)" />
            <circle cx="75" cy="20" r="15" stroke="#4A4A5E" strokeWidth="3" fill="rgba(255,255,255,0.3)" />
            <line x1="40" y1="20" x2="60" y2="20" stroke="#4A4A5E" strokeWidth="3" />
            <circle cx="25" cy="15" r="4" fill="rgba(255,255,255,0.8)" />
            <circle cx="75" cy="15" r="4" fill="rgba(255,255,255,0.8)" />
          </svg>
        </div>
      );
    
    case 'body':
      return (
        <div className="segment-body" style={{ background: gradients.secondary }}>
          <div className="vapor-texture"></div>
        </div>
      );
    
    case 'arm-left':
    case 'arm-right':
      return (
        <div className="segment-arm" style={{ background: gradients.tertiary }}>
          <div className="arm-glow"></div>
        </div>
      );
    
    case 'pen':
      return (
        <div className="segment-pen">
          <svg viewBox="0 0 80 30" width="100%" height="100%">
            <defs>
              <linearGradient id="penGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#7DF9FF" />
                <stop offset="100%" stopColor="#FF8EC6" />
              </linearGradient>
            </defs>
            <rect x="10" y="8" width="60" height="14" rx="7" fill="url(#penGradient)" />
            <polygon points="70,15 78,12 78,18" fill="#7DF9FF" filter="drop-shadow(0 0 5px #7DF9FF)" />
          </svg>
        </div>
      );
    
    case 'cloud':
      return (
        <div className="segment-cloud">
          <svg viewBox="0 0 100 60" width="100%" height="100%">
            <path d="M 20 40 Q 10 30 20 20 Q 30 15 40 20 Q 50 10 60 20 Q 70 15 80 25 Q 90 35 80 45 Q 70 50 60 45 Q 50 50 40 45 Q 30 50 20 40" 
                  fill="url(#cloudGradient)" opacity="0.7" />
            <defs>
              <linearGradient id="cloudGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#7DF9FF" stopOpacity="0.5" />
                <stop offset="100%" stopColor="#B49FCC" stopOpacity="0.6" />
              </linearGradient>
            </defs>
          </svg>
        </div>
      );
    
    case 'star':
      return (
        <div className="segment-star">
          <svg viewBox="0 0 50 50" width="100%" height="100%">
            <polygon points="25,5 30,20 45,20 33,30 38,45 25,35 12,45 17,30 5,20 20,20" 
                     fill="#FFD700" stroke="#4A4A5E" strokeWidth="2" />
          </svg>
        </div>
      );
    
    case 'heart':
      return (
        <div className="segment-heart">
          <svg viewBox="0 0 50 50" width="100%" height="100%">
            <path d="M 25 40 Q 15 30 10 22 Q 8 15 12 12 Q 18 8 25 15 Q 32 8 38 12 Q 42 15 40 22 Q 35 30 25 40" 
                  fill="#FF8EC6" stroke="#4A4A5E" strokeWidth="2" />
          </svg>
        </div>
      );
    
    case 'book':
      return (
        <div className="segment-book">
          <svg viewBox="0 0 60 70" width="100%" height="100%">
            <rect x="10" y="10" width="40" height="50" fill="#B49FCC" stroke="#4A4A5E" strokeWidth="2" rx="2" />
            <line x1="30" y1="10" x2="30" y2="60" stroke="#4A4A5E" strokeWidth="2" />
            <line x1="20" y1="25" x2="40" y2="25" stroke="#F4F1E8" strokeWidth="1.5" />
            <line x1="20" y1="35" x2="40" y2="35" stroke="#F4F1E8" strokeWidth="1.5" />
            <line x1="20" y1="45" x2="35" y2="45" stroke="#F4F1E8" strokeWidth="1.5" />
          </svg>
        </div>
      );
    
    default:
      return null;
  }
};

export default function SegmentedMascot() {
  return (
    <div className="segmented-mascot-layer">
      {segments.map((segment) => (
        <motion.div
          key={segment.id}
          className="segment-sticker"
          style={{
            left: `${segment.x}vw`,
            top: `${segment.y}vh`,
            width: segment.size,
            height: segment.size,
          }}
          initial={{ opacity: 0, scale: 0, rotate: 0 }}
          animate={{
            opacity: 1,
            scale: 1,
            rotate: segment.rotation,
            y: [0, -10, 0],
          }}
          transition={{
            opacity: { delay: segment.delay, duration: 0.5 },
            scale: { delay: segment.delay, duration: 0.5, type: 'spring' },
            rotate: { delay: segment.delay, duration: 0.5 },
            y: {
              delay: segment.delay + 0.5,
              duration: 3 + Math.random() * 2,
              repeat: Infinity,
              ease: 'easeInOut',
            },
          }}
          whileHover={{
            scale: 1.15,
            rotate: segment.rotation + 5,
            zIndex: 100,
            transition: { duration: 0.2 },
          }}
        >
          <SegmentContent type={segment.type} />
        </motion.div>
      ))}
    </div>
  );
}
