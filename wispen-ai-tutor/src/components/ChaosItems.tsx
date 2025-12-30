import { motion } from 'framer-motion';
import './ChaosItems.css';

interface ChaosItemProps {
    x: number;
    y: number;
    rotation: number;
    delay?: number;
}

interface ContentProps extends ChaosItemProps {
    content: string;
}

export const PaperBall = ({ x, y, rotation, delay = 0 }: ChaosItemProps) => {
    return (
        <motion.div
            className="chaos-item paper-ball"
            initial={{ x, y: y - 500, rotate: rotation, opacity: 0 }}
            animate={{ y, opacity: 1 }}
            transition={{
                type: "spring",
                bounce: 0.4,
                duration: 2,
                delay
            }}
            whileHover={{ y: y - 10 }}
            style={{ left: 0, top: 0 }} // Positioning handled by framer-motion x/y
        >
            <svg width="100%" height="100%" viewBox="0 0 60 60" style={{ overflow: 'visible' }}>
                {/* Crinkle lines */}
                <path d="M10,20 Q15,10 25,15 T40,10" fill="none" stroke="#999" strokeWidth="1" />
                <path d="M5,35 Q15,40 25,30 T45,45" fill="none" stroke="#999" strokeWidth="1" />
                <path d="M50,20 Q40,30 50,40" fill="none" stroke="#999" strokeWidth="1" />
                <path d="M20,50 Q30,40 40,50" fill="none" stroke="#999" strokeWidth="1" />
                <path d="M15,15 L45,45" fill="none" stroke="#999" strokeWidth="0.5" />
                <path d="M45,15 L15,45" fill="none" stroke="#999" strokeWidth="0.5" />
            </svg>
        </motion.div>
    );
};

export const TornPaper = ({ content, x, y, rotation, delay = 0 }: ContentProps) => {
    return (
        <motion.div
            className="chaos-item torn-paper"
            initial={{ x, y: y - 500, rotate: rotation, opacity: 0 }}
            animate={{ y, opacity: 1 }}
            transition={{
                type: "spring",
                damping: 15,
                duration: 1.5,
                delay
            }}
            style={{ left: 0, top: 0 }}
        >
            {content}
        </motion.div>
    );
};

export const ScribbledFormula = ({ content, x, y, rotation, delay = 0 }: ContentProps) => {
    return (
        <motion.div
            className="chaos-item scribbled-formula"
            initial={{ x, y: y - 500, rotate: rotation, opacity: 0 }}
            animate={{ y, opacity: 1 }}
            transition={{
                type: "spring",
                stiffness: 200,
                damping: 20,
                delay
            }}
            style={{ left: 0, top: 0 }}
        >
            {content}
            <svg className="scribble-overlay" viewBox="0 0 100 20" preserveAspectRatio="none">
                <path
                    d="M0,10 Q25,0 50,10 T100,10"
                    fill="none"
                    stroke="#d32f2f"
                    strokeWidth="3"
                    strokeLinecap="round"
                />
                <path
                    d="M0,10 Q25,20 50,10 T100,10"
                    fill="none"
                    stroke="#d32f2f"
                    strokeWidth="3"
                    strokeLinecap="round"
                    opacity="0.7"
                />
            </svg>
        </motion.div>
    );
};
