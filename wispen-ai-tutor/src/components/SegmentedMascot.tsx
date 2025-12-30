import { motion } from 'framer-motion';
import './SegmentedMascot.css';

interface SegmentedPart {
  id: string;
  type: 'head' | 'glasses' | 'body' | 'arm-left' | 'arm-right' | 'pen' | 'math-pi' | 'math-sigma' | 'chem-atom' | 'book' | 'math-eq' | 'trig' | 'calculus';
  x: number;
  y: number;
  rotation: number;
  size: number;
  delay: number;
}

const segments: SegmentedPart[] = [
  { id: 'math-pi-1', type: 'math-pi', x: 15, y: 10, rotation: -8, size: 80, delay: 0 },
  { id: 'math-sigma-1', type: 'math-sigma', x: 85, y: 15, rotation: 12, size: 80, delay: 0.2 },
  { id: 'chem-atom-1', type: 'chem-atom', x: 20, y: 70, rotation: -5, size: 100, delay: 0.4 },
  { id: 'math-eq-1', type: 'math-eq', x: 10, y: 45, rotation: 25, size: 120, delay: 0.6 },
  { id: 'trig-1', type: 'trig', x: 50, y: 20, rotation: -10, size: 90, delay: 0.8 },
  { id: 'calculus-1', type: 'calculus', x: 75, y: 35, rotation: 15, size: 100, delay: 1.0 },
];

const SegmentContent = ({ type }: { type: string }) => {
  switch (type) {
    case 'trig':
      return (
        <div className="segment-cloud">
          <svg viewBox="0 0 100 60" width="100%" height="100%">
            <text x="50%" y="60%" fontSize="24" textAnchor="middle" fill="#4A4A5E" opacity="0.5" fontFamily="serif" fontWeight="bold">
              sin²θ + cos²θ = 1
            </text>
          </svg>
        </div>
      );
    case 'calculus':
      return (
        <div className="segment-cloud">
          <svg viewBox="0 0 100 60" width="100%" height="100%">
            <text x="50%" y="60%" fontSize="24" textAnchor="middle" fill="#4A4A5E" opacity="0.5" fontFamily="serif" fontWeight="bold">
              ∫ x² dx = x³/3 + C
            </text>
          </svg>
        </div>
      );
    // ...existing cases...
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