import React, { useEffect, useRef, useState } from 'react';
import { Terminal } from 'lucide-react';

interface CheatDockProps {
  visible: boolean;
  onOpen: () => void;
  position: { x: number; y: number };
  onPositionChange: (pos: { x: number; y: number }) => void;
}

export const CheatDock: React.FC<CheatDockProps> = ({
  visible,
  onOpen,
  position,
  onPositionChange
}) => {
  const [dragging, setDragging] = useState(false);
  const dragRef = useRef({ startX: 0, startY: 0, startPosX: 0, startPosY: 0 });

  useEffect(() => {
    if (!dragging) return;

    const handleMove = (e: PointerEvent) => {
      const dx = e.clientX - dragRef.current.startX;
      const dy = e.clientY - dragRef.current.startY;
      onPositionChange({
        x: Math.max(8, dragRef.current.startPosX + dx),
        y: Math.max(80, dragRef.current.startPosY + dy)
      });
    };

    const handleUp = () => setDragging(false);

    window.addEventListener('pointermove', handleMove);
    window.addEventListener('pointerup', handleUp);
    return () => {
      window.removeEventListener('pointermove', handleMove);
      window.removeEventListener('pointerup', handleUp);
    };
  }, [dragging, onPositionChange]);

  if (!visible) return null;

  return (
    <button
      type="button"
      onClick={onOpen}
      onPointerDown={(e) => {
        dragRef.current = {
          startX: e.clientX,
          startY: e.clientY,
          startPosX: position.x,
          startPosY: position.y
        };
        setDragging(true);
      }}
      className="fixed z-[160] w-12 h-12 rounded-full bg-slate-900/90 border border-emerald-400/60 text-emerald-300 shadow-[0_0_20px_rgba(16,185,129,0.4)] flex items-center justify-center hover:scale-105 transition-transform"
      style={{ left: position.x, top: position.y }}
      title="Открыть читы"
    >
      <Terminal size={18} />
    </button>
  );
};
