import React from 'react';
import VideoCarousel from './VideoCarousel';
import { Pencil, Eraser, Ruler, TestTube1, Paperclip } from './StationeryItems';
import './AuthLayout.css';
import { motion } from 'framer-motion';

interface AuthLayoutProps {
    children: React.ReactNode;
    title: string;
    subtitle: string;
}

const AuthLayout = ({ children, title, subtitle }: AuthLayoutProps) => {
    return (
        <div className="auth-layout">
            <div className="auth-sidebar">
                <VideoCarousel />
                <div className="video-overlay-text">
                    <motion.h2
                        initial={{ y: 20, opacity: 0 }}
                        animate={{ y: 0, opacity: 1 }}
                        transition={{ delay: 0.5 }}
                    >
                        {title}
                    </motion.h2>
                    <motion.p
                        initial={{ y: 20, opacity: 0 }}
                        animate={{ y: 0, opacity: 1 }}
                        transition={{ delay: 0.7 }}
                    >
                        {subtitle}
                    </motion.p>
                </div>
            </div>

            <div className="auth-content">
                <div className="auth-decorations">
                    <Pencil style={{ position: 'absolute', top: '5%', right: '-40px', transform: 'rotate(-45deg)' }} />
                    <Eraser style={{ position: 'absolute', bottom: '10%', right: '5%', transform: 'rotate(15deg)' }} />
                    <Ruler style={{ position: 'absolute', top: '15%', left: '-20px', transform: 'rotate(90deg)' }} />
                    <TestTube1 style={{ position: 'absolute', bottom: '20%', left: '5%', transform: 'rotate(-10deg)' }} />
                    <Paperclip style={{ position: 'absolute', top: '50%', right: '2%', transform: 'rotate(45deg)' }} />
                </div>

                <div className="auth-form-container">
                    {children}
                </div>
            </div>
        </div>
    );
};

export default AuthLayout;
