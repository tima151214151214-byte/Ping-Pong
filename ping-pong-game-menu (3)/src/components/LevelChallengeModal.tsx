import React from 'react';
import { Crown, Trophy, XCircle } from 'lucide-react';

interface LevelChallengeModalProps {
  onTakeSafeLevel: () => void;
  onAcceptChallenge: () => void;
  onClose?: () => void;
}

export const LevelChallengeModal: React.FC<LevelChallengeModalProps> = ({
  onTakeSafeLevel,
  onAcceptChallenge,
  onClose
}) => {
  return (
    <div className="fixed inset-0 z-[220] flex items-center justify-center bg-black/90 backdrop-blur-xl">
      <div className="w-full max-w-xl bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl p-8 relative">
        {onClose && (
          <button onClick={onClose} className="absolute top-4 right-4 text-slate-400 hover:text-white">
            <XCircle size={24} />
          </button>
        )}
        <div className="text-center space-y-6">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-yellow-500/10 border border-yellow-500/50 text-yellow-400">
            <Crown size={32} />
          </div>
          <h2 className="text-3xl font-black text-white">УРОВЕНЬ 99 ДОСТИГНУТ</h2>
          <p className="text-slate-400">
            Вы на пороге легенды. Выберите безопасный путь или рискните ради 300 уровня.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4">
            <button
              onClick={onTakeSafeLevel}
              className="p-4 rounded-xl border border-emerald-500/50 bg-emerald-500/10 text-emerald-300 font-bold hover:bg-emerald-500/20 transition-all"
            >
              ВЗЯТЬ 100 УРОВЕНЬ
              <div className="text-xs text-emerald-200/70 mt-1">Без риска</div>
            </button>
            <button
              onClick={onAcceptChallenge}
              className="p-4 rounded-xl border border-red-500/50 bg-red-500/10 text-red-300 font-bold hover:bg-red-500/20 transition-all"
            >
              ВЫЗОВ НА 300
              <div className="text-xs text-red-200/70 mt-1">Проиграешь — уровень 0</div>
            </button>
          </div>

          <div className="mt-4 flex items-center justify-center gap-2 text-slate-500 text-xs">
            <Trophy size={14} /> Победи бота-легенду, чтобы получить 300 уровень.
          </div>
        </div>
      </div>
    </div>
  );
};
