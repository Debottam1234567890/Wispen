import { motion } from 'framer-motion';
import './GoldenTicketButton.css'; // Reusing styles

interface LeafButtonProps {
    onClick: () => void;
    text: string;
}

const LeafButton = ({ onClick, text }: LeafButtonProps) => {
    return (
        <motion.div
            className="golden-ticket-wrapper"
            initial={{ y: -50, opacity: 0, scale: 0.8, rotate: 5 }}
            animate={{
                y: 0,
                opacity: 1,
                scale: 1,
                rotate: 0
            }}
            transition={{
                duration: 0.8,
                ease: "backOut"
            }}
            onClick={onClick}
            style={{ margin: '20px auto', width: '300px', height: '180px' }} // Slightly smaller
        >
            <div className="golden-ticket glowing" style={{ width: '100%', height: '100%', borderColor: '#8b4513' }}>
                <div className="ticket-border" />
                <div className="ticket-content">
                    <div className="ticket-header">
                        <span className="ornament">✿</span>
                        <span className="ticket-title">OFFICIAL ENTRY</span>
                        <span className="ornament">✿</span>
                    </div>

                    <div className="ticket-main">
                        <span className="willy-wonka-text" style={{ fontSize: '2.5rem' }}>{text}</span>
                        <span className="ticket-tagline">Begin Your Journey</span>
                    </div>

                    <div className="ticket-footer">
                        <span className="ticket-number">No. 12345</span>
                        <span className="ticket-number">WISPEN</span>
                    </div>
                </div>
                {/* Leaf-like edges or cuts could be added with clip-path here if desired for more detail */}
                <div className="shimmer-overlay" />
            </div>
        </motion.div>
    );
};

export default LeafButton;
