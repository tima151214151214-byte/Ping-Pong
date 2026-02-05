import React from 'react';
import { Trophy, Star } from 'lucide-react';

interface CongratsModalProps {
  onClose: () => void;
}

export const CongratsModal: React.FC<CongratsModalProps> = ({ onClose }) => {
  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/95 backdrop-blur-xl animate-in fade-in duration-1000">
      <div className="max-w-2xl w-full p-8 text-center space-y-8 relative overflow-hidden">
        
        {/* Background Effects */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-gradient-to-r from-yellow-500/20 to-purple-500/20 rounded-full blur-[100px] animate-pulse pointer-events-none" />
        
        <div className="relative z-10 animate-in zoom-in duration-700 delay-200">
           <div className="inline-block p-6 rounded-full bg-gradient-to-br from-yellow-400 to-orange-600 mb-6 shadow-[0_0_50px_rgba(234,179,8,0.5)]">
             <Trophy size={80} className="text-white animate-bounce" />
           </div>
           
           <h1 className="text-6xl md:text-8xl font-black text-transparent bg-clip-text bg-gradient-to-r from-yellow-200 via-yellow-400 to-yellow-600 drop-shadow-sm mb-4">
             YOU WIN!
           </h1>
           
           <p className="text-xl md:text-2xl text-slate-300 font-bold tracking-widest uppercase mb-8">
             All Achievements Unlocked
           </p>

           <div className="grid grid-cols-3 gap-4 max-w-sm mx-auto mb-8 opacity-50">
              <Star className="text-yellow-500 w-full" />
              <Star className="text-yellow-500 w-full scale-125" />
              <Star className="text-yellow-500 w-full" />
           </div>

           <p className="text-slate-500 mb-8 max-w-lg mx-auto">
             You have proven yourself as the ultimate Pong Master (or the ultimate hacker). The game is yours.
           </p>

           <button 
             onClick={onClose}
             className="px-12 py-4 bg-white text-black font-black text-xl rounded-full hover:scale-110 transition-transform shadow-[0_0_30px_white]"
           >
             CONTINUE
           </button>
        </div>
      </div>
    </div>
  );
};
