import { motion } from 'framer-motion';

const UniverseBackground = () => {
    // Generate static stars to avoid re-rendering jitter
    const stars = Array.from({ length: 200 }).map((_, i) => ({
        id: i,
        cx: Math.random() * 100,
        cy: Math.random() * 100,
        r: Math.random() * 0.2 + 0.05,
        opacity: Math.random() * 0.7 + 0.3,
        duration: Math.random() * 3 + 2,
        delay: Math.random() * 2
    }));

    const shootingStars = Array.from({ length: 3 }).map((_, i) => ({
        id: i,
        delay: i * 5 + Math.random() * 5
    }));

    return (
        <div style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            background: 'linear-gradient(to bottom, #0f0c29, #302b63, #24243e)',
            zIndex: 0,
            overflow: 'hidden',
            pointerEvents: 'none'
        }}>
            <svg
                width="100%"
                height="100%"
                viewBox="0 0 100 100"
                preserveAspectRatio="none"
                style={{ position: 'absolute' }}
            >
                {/* Static/Twinkling Stars */}
                {stars.map((star) => (
                    <motion.circle
                        key={star.id}
                        cx={star.cx}
                        cy={star.cy}
                        r={star.r}
                        fill="white"
                        initial={{ opacity: star.opacity }}
                        animate={{ opacity: [star.opacity, star.opacity * 0.3, star.opacity] }}
                        transition={{
                            duration: star.duration,
                            repeat: Infinity,
                            delay: star.delay,
                            ease: "easeInOut"
                        }}
                    />
                ))}

                {/* Nebula Clouds (SVG Gradients) */}
                <defs>
                    <radialGradient id="nebula1" cx="20%" cy="30%" r="40%" fx="20%" fy="30%">
                        <stop offset="0%" stopColor="#ff00cc" stopOpacity="0.1" />
                        <stop offset="100%" stopColor="transparent" stopOpacity="0" />
                    </radialGradient>
                    <radialGradient id="nebula2" cx="80%" cy="70%" r="40%" fx="80%" fy="70%">
                        <stop offset="0%" stopColor="#3333ff" stopOpacity="0.1" />
                        <stop offset="100%" stopColor="transparent" stopOpacity="0" />
                    </radialGradient>
                </defs>

                <motion.rect
                    x="0" y="0" width="100" height="100" fill="url(#nebula1)"
                    animate={{ opacity: [0.5, 0.8, 0.5], scale: [1, 1.1, 1] }}
                    transition={{ duration: 20, repeat: Infinity, ease: "easeInOut" }}
                />
                <motion.rect
                    x="0" y="0" width="100" height="100" fill="url(#nebula2)"
                    animate={{ opacity: [0.5, 0.7, 0.5], scale: [1, 1.2, 1] }}
                    transition={{ duration: 25, repeat: Infinity, ease: "easeInOut", delay: 2 }}
                />
            </svg>

            {/* Shooting Stars */}
            {shootingStars.map(star => (
                <motion.div
                    key={star.id}
                    style={{
                        position: 'absolute',
                        top: '10%',
                        left: '10%',
                        width: '2px',
                        height: '2px',
                        background: 'white',
                        boxShadow: '0 0 4px 2px white',
                        borderRadius: '50%'
                    }}
                    initial={{ x: -100, y: -100, opacity: 0 }}
                    animate={{
                        x: ['0vw', '100vw'],
                        y: ['0vh', '100vh'],
                        opacity: [0, 1, 0]
                    }}
                    transition={{
                        duration: 1.5,
                        repeat: Infinity,
                        repeatDelay: 10 + Math.random() * 10,
                        delay: star.delay,
                        ease: "easeIn"
                    }}
                />
            ))}
        </div>
    );
};

export default UniverseBackground;
