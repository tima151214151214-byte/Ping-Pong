import React from 'react';
import { X, RotateCcw } from 'lucide-react';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  ballSizeMultiplier: number;
  onBallSizeChange: (val: number) => void;
  arenaTheme: 'CLASSIC' | 'NEON' | 'GRID' | 'SUNSET' | 'ICE' | 'VOID' | 'AUTUMN' | 'WINTER' | 'ROYAL';
  onArenaThemeChange: (theme: 'CLASSIC' | 'NEON' | 'GRID' | 'SUNSET' | 'ICE' | 'VOID' | 'AUTUMN' | 'WINTER' | 'ROYAL') => void;
  onReset: () => void;
  getThemeLabel?: (theme: 'CLASSIC' | 'NEON' | 'GRID' | 'SUNSET' | 'ICE' | 'VOID' | 'AUTUMN' | 'WINTER' | 'ROYAL') => string;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  ballSizeMultiplier,
  onBallSizeChange,
  arenaTheme,
  onArenaThemeChange,
  onReset,
  getThemeLabel,
}) => {
  if (!isOpen) return null;

  return (
    <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-md animate-in fade-in duration-200">
      <div className="w-full max-w-sm bg-slate-900 border border-slate-700 rounded-2xl p-6 shadow-2xl relative animate-in zoom-in-95 duration-200">
        <button 
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-white transition-colors"
        >
          <X size={24} />
        </button>

        <h2 className="text-2xl font-bold text-white mb-6 uppercase tracking-wider">Настройки</h2>

        <div className="space-y-8">
          {/* Arena Theme */}
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <label className="text-slate-300 font-medium">Карта</label>
              <span className="text-purple-400 font-mono font-bold">{arenaTheme}</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {(['NEON', 'CLASSIC', 'GRID', 'SUNSET', 'ICE', 'VOID', 'AUTUMN', 'WINTER', 'ROYAL'] as const).map((theme) => (
                <button
                  key={theme}
                  onClick={() => onArenaThemeChange(theme)}
                  className={`py-2 rounded-lg font-bold ${arenaTheme === theme ? 'bg-purple-600 text-white' : 'bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-white'}`}
                >
                  {getThemeLabel ? getThemeLabel(theme) : theme}
                </button>
              ))}
            </div>
          </div>

          {/* Ball Size Control */}
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <label className="text-slate-300 font-medium">Размер мяча</label>
              <span className="text-cyan-400 font-mono font-bold">x{ballSizeMultiplier.toFixed(1)}</span>
            </div>
            <input
              type="range"
              min="1"
              max="3"
              step="0.5"
              value={ballSizeMultiplier}
              onChange={(e) => onBallSizeChange(parseFloat(e.target.value))}
              className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-cyan-500"
            />
            <div className="flex justify-between text-xs text-slate-500 font-mono">
              <span>НОРМА</span>
              <span>ГИГАНТ</span>
            </div>
          </div>

          {/* Reset Button */}
          <button
            onClick={onReset}
            className="w-full py-3 rounded-xl bg-slate-800 text-slate-300 font-bold hover:bg-slate-700 hover:text-white transition-all flex items-center justify-center gap-2"
          >
            <RotateCcw size={18} />
            Сбросить настройки
          </button>
        </div>
      </div>
    </div>
  );
};
