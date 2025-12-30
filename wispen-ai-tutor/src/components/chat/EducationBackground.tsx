import { motion } from 'framer-motion';

const EducationBackground = () => {
    // Stationery items configuration
    // We'll use the SVGs extracted from App.tsx
    const floatingItems = [
        {
            id: 'pencil-1',
            type: 'pencil',
            initial: { x: '10%', y: '15%', rotate: -15 },
            animate: { y: ['15%', '18%', '15%'], rotate: [-15, -10, -15] },
            duration: 6
        },
        {
            id: 'book-1',
            type: 'book',
            initial: { x: '85%', y: '70%', rotate: 10 },
            animate: { y: ['70%', '65%', '70%'], rotate: [10, 5, 10] },
            duration: 7
        },
        {
            id: 'eraser-1',
            type: 'eraser',
            initial: { x: '20%', y: '80%', rotate: 5 },
            animate: { y: ['80%', '83%', '80%'], rotate: [5, 10, 5] },
            duration: 5.5
        },
        {
            id: 'ruler-1',
            type: 'ruler',
            initial: { x: '80%', y: '20%', rotate: 45 },
            animate: { y: ['20%', '22%', '20%'], rotate: [45, 40, 45] },
            duration: 8
        },
        {
            id: 'protractor-1',
            type: 'protractor',
            initial: { x: '15%', y: '50%', rotate: -10 },
            animate: { y: ['50%', '45%', '50%'], rotate: [-10, -5, -10] },
            duration: 6.5
        },
        {
            id: 'test-tube-aquamarine',
            type: 'test-tube-1',
            initial: { x: '75%', y: '40%', rotate: 15 },
            animate: { y: ['40%', '43%', '40%'], rotate: [15, 20, 15] },
            duration: 7.2
        },
        {
            id: 'test-tube-pink',
            type: 'test-tube-2',
            initial: { x: '5%', y: '30%', rotate: -20 },
            animate: { y: ['30%', '28%', '30%'], rotate: [-20, -25, -20] },
            duration: 6.8
        },
        {
            id: 'paperclip-1',
            type: 'paperclip',
            initial: { x: '90%', y: '10%', rotate: 30 },
            animate: { y: ['10%', '15%', '10%'], rotate: [30, 60, 30] },
            duration: 9
        }
    ];

    return (
        <div style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            background: '#f4f6f9', // Light dreamy background
            backgroundImage: 'radial-gradient(#e0e5ec 1px, transparent 1px)',
            backgroundSize: '30px 30px',
            zIndex: 0,
            overflow: 'hidden',
            pointerEvents: 'none'
        }}>
            {floatingItems.map(item => (
                <motion.div
                    key={item.id}
                    style={{
                        position: 'absolute',
                        left: item.initial.x,
                        top: item.initial.y,
                        // Using CSS classes from App.css usually, but since we are in a component 
                        // and want to ensure they look right without global dependencies if possible,
                        // I'll inline the SVG content logic here or use the classes if I can't.
                        // For simplicity and robustness, I will inline the SVG render logic based on type.
                    }}
                    initial={{ rotate: item.initial.rotate }}
                    animate={item.animate}
                    transition={{ duration: item.duration, repeat: Infinity, ease: "easeInOut" }}
                >
                    {renderStationeryItem(item.type)}
                </motion.div>
            ))}
        </div>
    );
};

const renderStationeryItem = (type: string) => {
    switch (type) {
        case 'pencil':
            // Simple CSS/Div pencil representation or SVG
            return (
                <div style={{
                    width: '20px', height: '100px', background: '#FFD700',
                    borderRadius: '2px', position: 'relative',
                    boxShadow: '2px 2px 5px rgba(0,0,0,0.1)'
                }}>
                    <div style={{ position: 'absolute', top: 0, width: '100%', height: '15px', background: '#ff9999', borderRadius: '2px 2px 0 0' }} /> {/* Eraser */}
                    <div style={{ position: 'absolute', bottom: -15, width: 0, height: 0, borderLeft: '10px solid transparent', borderRight: '10px solid transparent', borderTop: '15px solid #d2b48c' }} /> {/* Wood tip */}
                    <div style={{ position: 'absolute', bottom: -22, left: 7, width: 0, height: 0, borderLeft: '3px solid transparent', borderRight: '3px solid transparent', borderTop: '7px solid #333' }} /> {/* Lead */}
                </div>
            );
        case 'book':
            return (
                <div style={{
                    width: '60px', height: '80px', background: '#5dADE2',
                    borderRadius: '4px 8px 8px 4px',
                    boxShadow: '3px 3px 8px rgba(0,0,0,0.15)',
                    borderLeft: '8px solid #34495E',
                    display: 'flex', alignItems: 'center', justifyContent: 'center'
                }}>
                    <div style={{ width: '40px', height: '2px', background: 'rgba(255,255,255,0.3)', marginBottom: '10px' }} />
                </div>
            );
        case 'eraser':
            return (
                <div style={{
                    width: '50px', height: '30px', background: 'white',
                    borderRadius: '4px', transform: 'skew(-10deg)',
                    boxShadow: '2px 2px 5px rgba(0,0,0,0.1)',
                    border: '1px solid #ddd',
                    display: 'flex', flexDirection: 'row'
                }}>
                    <div style={{ width: '40%', height: '100%', background: '#ff99cc', borderRadius: '4px 0 0 4px' }} />
                </div>
            );
        case 'ruler':
            return (
                <div style={{
                    width: '150px', height: '30px', background: 'rgba(255,255,255,0.8)',
                    border: '1px solid #ccc', borderRadius: '4px',
                    display: 'flex', alignItems: 'flex-end', paddingBottom: '5px',
                    boxShadow: '2px 2px 5px rgba(0,0,0,0.05)'
                }}>
                    {[...Array(15)].map((_, i) => (
                        <div key={i} style={{ width: '1px', height: i % 5 === 0 ? '15px' : '8px', background: '#999', marginLeft: '9px' }} />
                    ))}
                </div>
            );
        case 'protractor':
            return (
                <svg width="100" height="50" viewBox="0 0 100 50" style={{ filter: 'drop-shadow(2px 2px 4px rgba(0,0,0,0.1))' }}>
                    <path d="M10,40 A40,40 0 0,1 90,40" fill="rgba(255,255,255,0.7)" stroke="#4A4A5E" strokeWidth="1" />
                    <line x1="10" y1="40" x2="90" y2="40" stroke="#4A4A5E" strokeWidth="1" />
                    <line x1="50" y1="40" x2="50" y2="10" stroke="#4A4A5E" strokeWidth="1" />
                    <path d="M20,40 A30,30 0 0,1 80,40" fill="none" stroke="#4A4A5E" strokeWidth="0.5" strokeDasharray="3,3" />
                </svg>
            );
        case 'test-tube-1':
            return (
                <svg width="40" height="120" viewBox="0 0 40 120" style={{ filter: 'drop-shadow(2px 2px 5px rgba(0,0,0,0.1))' }}>
                    <path d="M10,10 L10,100 A10,10 0 0,0 30,100 L30,10" fill="rgba(255, 255, 255, 0.4)" stroke="#888" strokeWidth="2" />
                    <path d="M12,60 L12,98 A8,8 0 0,0 28,98 L28,60 Z" fill="#7fffd4" opacity="0.6" />
                    <circle cx="16" cy="55" r="2" fill="#7fffd4" opacity="0.8" />
                    <circle cx="24" cy="50" r="3" fill="#7fffd4" opacity="0.6" />
                </svg>
            );
        case 'test-tube-2':
            return (
                <svg width="35" height="100" viewBox="0 0 35 100" style={{ filter: 'drop-shadow(2px 2px 5px rgba(0,0,0,0.1))' }}>
                    <path d="M8,10 L8,85 A9,9 0 0,0 26,85 L26,10" fill="rgba(255, 255, 255, 0.4)" stroke="#888" strokeWidth="2" />
                    <path d="M10,40 L10,83 A7,7 0 0,0 24,83 L24,40 Z" fill="#ff69b4" opacity="0.6" />
                    <circle cx="17" cy="35" r="2" fill="#ff69b4" opacity="0.8" />
                </svg>
            );
        case 'paperclip':
            return (
                <svg width="30" height="60" viewBox="0 0 30 60" style={{ filter: 'drop-shadow(1px 1px 2px rgba(0,0,0,0.1))' }}>
                    <path d="M10,20 L10,50 A10,10 0 0,0 30,50 L30,10 A6,6 0 0,0 18,10 L18,40"
                        fill="none" stroke="#777" strokeWidth="3" opacity="0.8" strokeLinecap="round" />
                </svg>
            );
        default:
            return null;
    }
};

export default EducationBackground;
