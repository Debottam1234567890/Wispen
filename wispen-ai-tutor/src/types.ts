export interface WispenMascotProps {
  onGlassesClick?: () => void;
  onPenWrite?: (word: string) => void;
}

export interface FloatingButtonProps {
  text: string;
  icon: React.ReactNode;
  gradient: string;
  rotation: number;
  onClick?: () => void;
}

export interface StickyNoteProps {
  content: string;
  initialX: number;
  initialY: number;
  driftSpeed: number;
  rotation: number;
}

export interface InkTrailProps {
  mousePosition: { x: number; y: number };
  isActive: boolean;
}

export interface ParticleProps {
  x: number;
  y: number;
  type: 'sparkle' | 'dust' | 'ink';
  id: string;
}

export interface MousePosition {
  x: number;
  y: number;
}