import { motion } from 'framer-motion';

export const Pencil = ({ style }: { style?: React.CSSProperties }) => (
    <div className="stationery-item pencil" style={style} />
);

export const Book = ({ style }: { style?: React.CSSProperties }) => (
    <div className="stationery-item book" style={style} />
);

export const Eraser = ({ style }: { style?: React.CSSProperties }) => (
    <div className="stationery-item eraser" style={style} />
);

export const Bookmark = ({ style }: { style?: React.CSSProperties }) => (
    <div className="stationery-item bookmark" style={style} />
);

export const Paperclip = ({ style }: { style?: React.CSSProperties }) => (
    <div className="stationery-item paperclip" style={style}>
        <svg width="30" height="60" viewBox="0 0 30 60">
            <path d="M10,20 L10,50 A10,10 0 0,0 30,50 L30,10 A6,6 0 0,0 18,10 L18,40"
                fill="none" stroke="#777" strokeWidth="3" opacity="0.8" strokeLinecap="round" />
        </svg>
    </div>
);

export const Ruler = ({ style }: { style?: React.CSSProperties }) => (
    <div className="stationery-item ruler" style={style}>
        {[...Array(10)].map((_, i) => (
            <div key={i} className="ruler-mark" />
        ))}
    </div>
);

export const Protractor = ({ style }: { style?: React.CSSProperties }) => (
    <div className="stationery-item protractor" style={style}>
        <svg width="100" height="50" viewBox="0 0 100 50">
            <path d="M10,40 A40,40 0 0,1 90,40" fill="none" stroke="#4A4A5E" strokeWidth="1" strokeDasharray="2,2" />
            <line x1="50" y1="40" x2="50" y2="10" stroke="#4A4A5E" strokeWidth="1" />
        </svg>
    </div>
);

export const TestTube1 = ({ style }: { style?: React.CSSProperties }) => (
    <div className="stationery-item test-tube-1" style={style}>
        <svg width="40" height="120" viewBox="0 0 40 120">
            <path d="M10,10 L10,100 A10,10 0 0,0 30,100 L30,10" fill="rgba(255, 255, 255, 0.4)" stroke="#4A4A5E" strokeWidth="2" />
            <path d="M12,60 L12,98 A8,8 0 0,0 28,98 L28,60 Z" fill="#7fffd4" opacity="0.6" />
            <circle cx="16" cy="55" r="2" fill="#7fffd4" opacity="0.8" />
            <circle cx="24" cy="50" r="3" fill="#7fffd4" opacity="0.6" />
        </svg>
    </div>
);

export const TestTube2 = ({ style }: { style?: React.CSSProperties }) => (
    <div className="stationery-item test-tube-2" style={style}>
        <svg width="35" height="100" viewBox="0 0 35 100">
            <path d="M8,10 L8,85 A9,9 0 0,0 26,85 L26,10" fill="rgba(255, 255, 255, 0.4)" stroke="#4A4A5E" strokeWidth="2" />
            <path d="M10,40 L10,83 A7,7 0 0,0 24,83 L24,40 Z" fill="#ff69b4" opacity="0.6" />
            <circle cx="17" cy="35" r="2" fill="#ff69b4" opacity="0.8" />
        </svg>
    </div>
);

export const FloatingEquation = ({ item, index }: { item: string, index: number }) => (
    <motion.div
        className="equation"
        initial={{
            opacity: 0,
            scale: 0.8,
            x: Math.random() * (typeof window !== 'undefined' ? window.innerWidth : 800),
            y: Math.random() * (typeof window !== 'undefined' ? window.innerHeight : 600)
        }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{
            duration: 1,
            delay: index * 0.2,
            repeat: Infinity,
            repeatType: "reverse"
        }}
    >
        {item}
    </motion.div>
);
