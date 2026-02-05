import React from 'react';
import { PlayerSide, OpponentType } from '../types';
import { Shield, ChevronLeft } from 'lucide-react';

interface TeamSelectProps {
  opponent: OpponentType;
  onSelect: (side: PlayerSide) => void;
  onBack: () => void;
}

export const TeamSelect: React.FC<TeamSelectProps> = ({ opponent, onSelect, onBack }) => {
  return (
    <div className="flex flex-col items-center justify-center space-y-8 animate-in slide-in-from-bottom-10 fade-in duration-500 w-full max-w-4xl mx-auto p-4">
      
      <button 
        onClick={onBack}
        className="self-start md:self-center flex items-center gap-2 text-slate-500 hover:text-white transition-colors absolute top-4 left-4 md:static md:mb-4"
      >
        <ChevronLeft size={20} /> Назад
      </button>

      <div className="text-center">
        <h2 className="text-3xl md:text-4xl font-bold text-white mb-4 uppercase tracking-widest drop-shadow-glow">
          ВЫБЕРИ СТОРОНУ
        </h2>
        <p className="text-slate-400 max-w-md mx-auto">
          {opponent === 'FRIEND' 
            ? "Игрок 1, выбери свой цвет. Игрок 2 будет играть за противоположную команду." 
            : "Выбери цвет своей команды для начала матча."}
        </p>
      </div>

      <div className="flex flex-col md:flex-row gap-6 w-full justify-center items-center">
        {/* Red Team */}
        <button
          onClick={() => onSelect('RED')}
          className="group relative w-full max-w-sm md:w-64 h-64 md:h-80 rounded-3xl bg-gradient-to-br from-slate-900 to-red-950/30 border border-red-900/50 hover:border-red-500 hover:shadow-[0_0_50px_-10px_rgba(239,68,68,0.4)] transition-all duration-300 flex flex-col items-center justify-center gap-4 md:gap-6 overflow-hidden"
        >
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-red-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
          
          <div className="p-4 md:p-6 rounded-full bg-red-500/10 text-red-500 group-hover:scale-110 group-hover:bg-red-500 group-hover:text-black transition-all duration-300 shadow-[0_0_20px_rgba(239,68,68,0.2)]">
            <Shield size={48} className="md:w-16 md:h-16" />
          </div>
          <div className="text-center z-10">
            <span className="block text-2xl md:text-3xl font-black text-red-500 tracking-tighter">КРАСНЫЕ</span>
            <span className="block text-slate-500 text-xs uppercase tracking-[0.2em] group-hover:text-red-300 mt-2">СЛЕВА</span>
          </div>
        </button>

        <div className="text-slate-600 font-bold text-xl">VS</div>

        {/* Blue Team */}
        <button
          onClick={() => onSelect('BLUE')}
          className="group relative w-full max-w-sm md:w-64 h-64 md:h-80 rounded-3xl bg-gradient-to-br from-slate-900 to-blue-950/30 border border-blue-900/50 hover:border-blue-500 hover:shadow-[0_0_50px_-10px_rgba(59,130,246,0.4)] transition-all duration-300 flex flex-col items-center justify-center gap-4 md:gap-6 overflow-hidden"
        >
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-blue-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />

          <div className="p-4 md:p-6 rounded-full bg-blue-500/10 text-blue-500 group-hover:scale-110 group-hover:bg-blue-500 group-hover:text-black transition-all duration-300 shadow-[0_0_20px_rgba(59,130,246,0.2)]">
            <Shield size={48} className="md:w-16 md:h-16" />
          </div>
          <div className="text-center z-10">
            <span className="block text-2xl md:text-3xl font-black text-blue-500 tracking-tighter">СИНИЕ</span>
            <span className="block text-slate-500 text-xs uppercase tracking-[0.2em] group-hover:text-blue-300 mt-2">СПРАВА</span>
          </div>
        </button>
      </div>
    </div>
  );
};
