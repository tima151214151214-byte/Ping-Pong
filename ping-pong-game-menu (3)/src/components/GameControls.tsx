import React from 'react';
import { OpponentType, PlayerSide } from '../types';

interface GameControlsProps {
  opponent: OpponentType;
  playerSide: PlayerSide;
  onMoveLeft: (value: number) => void;
  onMoveRight: (value: number) => void;
  isMultiplayer?: boolean;
}

const StyledRange = ({
  color,
  onChange,
  label,
  thumbScale = 1
}: {
  color: 'red' | 'blue';
  onChange: (val: number) => void;
  label?: string;
  thumbScale?: number;
}) => {
  return (
    <div
      className="flex flex-col items-center w-full max-w-[45%] md:max-w-xs mx-auto"
      style={{ ['--thumb-size' as any]: `${Math.max(6, Math.min(20, 8 * thumbScale))}px` }}
    >
      {label && (
        <span className={`mb-2 font-mono text-[10px] uppercase tracking-[0.2em] font-bold ${color === 'red' ? 'text-red-500' : 'text-blue-500'}`}>
          {label}
        </span>
      )}
      
      <div className="relative w-full h-10 flex items-center justify-center">
        {/* Track Background */}
        <div className="absolute inset-x-0 h-1 bg-slate-800 rounded-full overflow-hidden pointer-events-none">
           <div className={`h-full w-full opacity-30 ${color === 'red' ? 'bg-red-500' : 'bg-blue-500'}`} />
        </div>

        <input
          type="range"
          min="0"
          max="100"
          defaultValue="50"
          step="0.1" // Smooth movement
          className={`
            range-control appearance-none bg-transparent w-full h-full cursor-pointer z-10
            focus:outline-none
            [&::-webkit-slider-thumb]:appearance-none
            [&::-webkit-slider-thumb]:bg-white
            [&::-webkit-slider-thumb]:rounded-full
            [&::-webkit-slider-thumb]:shadow-[0_0_10px_rgba(255,255,255,0.8)]
            [&::-webkit-slider-thumb]:transition-transform
            [&::-webkit-slider-thumb]:active:scale-150
            
            [&::-moz-range-thumb]:bg-white
            [&::-moz-range-thumb]:border-none
            [&::-moz-range-thumb]:rounded-full
          `}
          onChange={(e) => onChange(parseFloat(e.target.value))}
        />
      </div>
    </div>
  );
};

export const GameControls: React.FC<GameControlsProps> = ({
  opponent,
  playerSide,
  onMoveLeft,
  onMoveRight,
  isMultiplayer
}) => {
  if (opponent === 'FRIEND' && !isMultiplayer) {
    return (
      <div className="absolute bottom-6 left-0 right-0 px-4 flex justify-between items-end z-20 w-full gap-8">
        <StyledRange 
          color="red" 
          label="КРАСНЫЕ" 
          onChange={(val) => onMoveLeft(val)} 
          thumbScale={(window as any).__cheatThumbScale || 1}
        />
        <StyledRange 
          color="blue" 
          label="СИНИЕ" 
          onChange={(val) => onMoveRight(val)} 
          thumbScale={(window as any).__cheatThumbScale || 1}
        />
      </div>
    );
  }

  return (
    <div className="absolute bottom-6 left-0 right-0 px-4 flex justify-center items-end z-20 w-full">
      <StyledRange 
        color={playerSide === 'RED' ? 'red' : 'blue'} 
        label="УПРАВЛЕНИЕ" 
        onChange={(val) => {
          if (playerSide === 'RED') onMoveLeft(val);
          else onMoveRight(val);
        }} 
        thumbScale={(window as any).__cheatThumbScale || 1}
      />
    </div>
  );
};
