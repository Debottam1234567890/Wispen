import { useState } from 'react';
import Header from './components/Header';
import WispenMascot from './components/WispenMascot';
import StickyNote from './components/StickyNote';
import InkTrail from './components/InkTrail';
import ParticleSystem from './components/ParticleSystem';
import BackgroundDoodles from './components/BackgroundDoodles';
import SegmentedMascot from './components/SegmentedMascot';
import GoldenTicketButton from './components/GoldenTicketButton';
import MarkerButton from './components/MarkerButton';
import './App.css';

const STUDY_TIPS = [
  "Take breaks every 25 minutes! 🧠",
  "Teach what you learn to remember better 📚",
  "Practice makes perfect! ✨",
  "Stay curious, stay creative 🎨",
  "Ask questions, explore answers 🔍",
  "Learn by doing, not just reading 💡",
  "Mistakes are learning opportunities 🌟",
  "Connect new ideas to what you know 🔗",
  "Sleep improves memory consolidation 😴",
  "Exercise boosts brain power 🏃",
  "Stay hydrated for better focus 💧",
  "Review notes within 24 hours 📝",
  "Use mnemonics for better recall 🎯",
  "Study in short, focused sessions ⏰",
  "Visualize concepts to understand better 🖼️",
  "Test yourself frequently 📋",
  "Explain concepts out loud 🗣️",
  "Create mind maps for connections 🧩"
];

function App() {
  const [, setGlassesClicked] = useState(false);

  const handleGlassesClick = () => {
    setGlassesClicked(true);
    console.log("WISPEN's glasses clicked! 👓");
  };

  const handlePenWrite = (word: string) => {
    console.log(`WISPEN wrote: ${word} ✨`);
  };

  const handleGoldenTicketClick = () => {
    console.log('Golden Ticket - Getting Started clicked!');
    alert('🎫 Welcome to your Learning Adventure! Let\'s begin your journey with WISPEN! 🎉');
  };

  const handleMarkerButtonClick = () => {
    console.log('Marker Button - Check Your Progress clicked!');
    alert('📊 Time to check your amazing progress! Keep up the great work! 🌟');
  };

  return (
    <div className="app">
      {/* Background Effects */}
      <BackgroundDoodles />
      <ParticleSystem />
      <InkTrail />
      <SegmentedMascot />

      {/* Floating Sticky Notes - Increased from 6 to 15 */}
      {[...Array(15)].map((_, i) => (
        <StickyNote
          key={i}
          content={STUDY_TIPS[i]}
          initialX={Math.random() * (window.innerWidth - 100)}
          initialY={Math.random() * (window.innerHeight - 100)}
          driftSpeed={15 + Math.random() * 10}
          rotation={-10 + Math.random() * 20}
        />
      ))}

      {/* Main Content */}
      <div className="content">
        <Header />

        {/* Mascot Zone */}
        <div className="mascot-zone">
          <WispenMascot 
            onGlassesClick={handleGlassesClick}
            onPenWrite={handlePenWrite}
          />
        </div>

        {/* Button Zone - New Special Buttons */}
        <div className="button-zone">
          <GoldenTicketButton onClick={handleGoldenTicketClick} />
          <MarkerButton onClick={handleMarkerButtonClick} />
        </div>
      </div>
    </div>
  );
}

export default App;