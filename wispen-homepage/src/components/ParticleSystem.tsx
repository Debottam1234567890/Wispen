import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { ParticleProps } from '../types';
import './ParticleSystem.css';

export default function ParticleSystem() {
  const [particles, setParticles] = useState<ParticleProps[]>([]);

  useEffect(() => {
    const interval = setInterval(() => {
      const newParticle: ParticleProps = {
        x: Math.random() * window.innerWidth,
        y: window.innerHeight + 20,
        type: Math.random() > 0.5 ? 'sparkle' : 'dust',
        id: `particle-${Date.now()}-${Math.random()}`
      };

      setParticles(prev => [...prev, newParticle].slice(-30));
    }, 500);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="particle-system">
      <AnimatePresence>
        {particles.map(particle => (
          <motion.div
            key={particle.id}
            className={`particle particle-${particle.type}`}
            initial={{ 
              x: particle.x, 
              y: particle.y,
              opacity: 0,
              scale: 0
            }}
            animate={{ 
              y: particle.y - window.innerHeight - 100,
              opacity: [0, 0.6, 0.6, 0],
              scale: [0, 1, 1, 0],
              rotate: Math.random() * 360
            }}
            exit={{ opacity: 0 }}
            transition={{ 
              duration: 8,
              ease: "linear"
            }}
          >
            {particle.type === 'sparkle' ? '✨' : '•'}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}