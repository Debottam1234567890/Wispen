import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { MousePosition } from '../types';
import './InkTrail.css';

interface TrailPoint extends MousePosition {
  id: number;
  timestamp: number;
}

export default function InkTrail() {
  const [trailPoints, setTrailPoints] = useState<TrailPoint[]>([]);

  useEffect(() => {
    let pointId = 0;

    const handleMouseMove = (e: MouseEvent) => {
      const newPoint: TrailPoint = {
        x: e.clientX,
        y: e.clientY,
        id: pointId++,
        timestamp: Date.now()
      };

      setTrailPoints(prev => [...prev, newPoint].slice(-15));
    };

    window.addEventListener('mousemove', handleMouseMove);

    // Clean up old points
    const interval = setInterval(() => {
      const now = Date.now();
      setTrailPoints(prev => prev.filter(point => now - point.timestamp < 2000));
    }, 100);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      clearInterval(interval);
    };
  }, []);

  return (
    <div className="ink-trail-container">
      <AnimatePresence>
        {trailPoints.map((point, index) => (
          <motion.div
            key={point.id}
            className="ink-trail-point"
            initial={{ opacity: 0.8, scale: 1 }}
            animate={{ opacity: 0, scale: 0.5 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 2 }}
            style={{
              left: point.x,
              top: point.y,
              width: Math.max(3, 8 - index * 0.3),
              height: Math.max(3, 8 - index * 0.3),
            }}
          />
        ))}
      </AnimatePresence>
    </div>
  );
}