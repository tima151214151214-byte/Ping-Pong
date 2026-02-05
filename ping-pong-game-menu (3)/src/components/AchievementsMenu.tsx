import React, { useMemo, useState } from 'react';
import { Achievement } from '../types';
import { X, Trophy, Lock } from 'lucide-react';

import { Zap } from 'lucide-react';

interface AchievementsMenuProps {
  achievements: Achievement[];
  onClose: () => void;
  stats: { totalWins: number; totalLosses: number; totalExits: number; totalScore: number; totalGamesPlayed: number; level: number };
  onUnlockAll?: () => void;
  onToggle?: (id: string) => void;
}

const AchievementsMenu: React.FC<AchievementsMenuProps> = ({ achievements, onClose, stats, onUnlockAll, onToggle }) => {
  const unlockedCount = useMemo(() => achievements.filter(a => a.isUnlocked).length, [achievements]);
  const progress = Math.round((unlockedCount / achievements.length) * 100);
  const [toast, setToast] = useState<string | null>(null);

  const handleToggle = (id: string, title: string, wasUnlocked: boolean) => {
    if (!onToggle) return;
    onToggle(id);
    if (!wasUnlocked) {
      const messages = [
        `✅ Достижение получено: ${title}`,
        `🔥 Вот это да! ${title}`,
        `⚡ Сложно было? ${title} твой!`,
        `🏆 Поздравляем! ${title}`,
        `😎 Красиво! ${title}`,
      ];
      const msg = messages[Math.floor(Math.random() * messages.length)];
      setToast(msg);
      setTimeout(() => setToast(null), 2000);
    }
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'bronze': return 'border-orange-700 bg-orange-900/20 text-orange-200';
      case 'silver': return 'border-slate-400 bg-slate-800/40 text-slate-200';
      case 'gold': return 'border-yellow-500 bg-yellow-900/20 text-yellow-200';
      case 'platinum': return 'border-cyan-400 bg-cyan-900/20 text-cyan-200';
      case 'secret': return 'border-purple-500 bg-purple-900/20 text-purple-200';
      default: return 'border-gray-700 bg-gray-900/50';
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="w-full max-w-4xl h-[90vh] bg-slate-900 border border-slate-700 rounded-2xl flex flex-col shadow-2xl relative overflow-hidden">
        
        {/* Header */}
        <div className="p-6 border-b border-slate-700 flex justify-between items-center bg-slate-800/50">
          <div>
            <h2 className="text-3xl font-bold text-white flex items-center gap-3">
              <Trophy className="text-yellow-400" size={32} />
              Достижения (Achievements)
            </h2>
            <div className="mt-2 text-slate-400 text-sm">
              Прогресс: {unlockedCount} / {achievements.length} ({progress}%)
            </div>
          </div>
          <div className="flex gap-2">
            {onUnlockAll && (
              <div className="flex gap-2 items-center">
                <button
                  onClick={onUnlockAll}
                  className="flex items-center gap-1 px-3 py-1 bg-yellow-600/20 text-yellow-500 border border-yellow-500/50 rounded-lg hover:bg-yellow-500 hover:text-black transition-all text-xs font-bold uppercase"
                >
                  <Zap size={14} /> Unlock All
                </button>
                {onToggle && (
                  <span className="text-[10px] text-slate-400 uppercase tracking-widest">Можно открывать по одному</span>
                )}
              </div>
            )}
            <button 
              onClick={onClose}
              className="p-2 hover:bg-slate-700 rounded-full transition-colors"
            >
              <X className="text-white" size={24} />
            </button>
          </div>
        </div>

        {toast && (
          <div className="absolute top-4 left-1/2 -translate-x-1/2 bg-emerald-500/20 border border-emerald-400 text-emerald-100 px-4 py-2 rounded-full text-sm font-bold shadow-lg">
            {toast}
          </div>
        )}

        {/* Stats Bar */}
        <div className="grid grid-cols-3 gap-4 p-4 bg-slate-950/50 border-b border-slate-800">
          <div className="text-center">
            <div className="text-xs text-slate-500 uppercase tracking-wider">Побед</div>
            <div className="text-xl font-mono text-green-400">{stats.totalWins}</div>
          </div>
          <div className="text-center">
            <div className="text-xs text-slate-500 uppercase tracking-wider">Поражений</div>
            <div className="text-xl font-mono text-red-400">{stats.totalLosses}</div>
          </div>
          <div className="text-center">
            <div className="text-xs text-slate-500 uppercase tracking-wider">Выходов</div>
            <div className="text-xl font-mono text-yellow-400">{stats.totalExits}</div>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4 p-4 bg-slate-950/30 border-b border-slate-800">
          <div className="text-center">
            <div className="text-xs text-slate-500 uppercase tracking-wider">Всего очков</div>
            <div className="text-xl font-mono text-blue-400">{stats.totalScore}</div>
          </div>
          <div className="text-center">
            <div className="text-xs text-slate-500 uppercase tracking-wider">Игр сыграно</div>
            <div className="text-xl font-mono text-purple-400">{stats.totalGamesPlayed}</div>
          </div>
          <div className="text-center">
            <div className="text-xs text-slate-500 uppercase tracking-wider">Уровень</div>
            <div className="text-xl font-mono text-emerald-400">{stats.level}</div>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="w-full h-2 bg-slate-800">
          <div 
            className="h-full bg-gradient-to-r from-yellow-600 to-yellow-300 transition-all duration-1000"
            style={{ width: `${progress}%` }}
          />
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto p-6 space-y-3 custom-scrollbar">
          {achievements.map((achievement) => (
            <div 
              key={achievement.id}
              onClick={() => handleToggle(achievement.id, achievement.title, achievement.isUnlocked)}
              className={`
                relative flex items-center gap-4 p-4 rounded-xl border transition-all duration-300
                ${achievement.isUnlocked ? getCategoryColor(achievement.category) : 'border-slate-800 bg-slate-900/80 opacity-60 grayscale'}
                ${achievement.isUnlocked ? 'shadow-[0_0_15px_rgba(0,0,0,0.3)]' : ''}
                ${onToggle ? 'cursor-pointer hover:scale-[1.01] hover:brightness-110' : ''}
              `}
            >
              <div className={`
                flex-shrink-0 w-12 h-12 rounded-full flex items-center justify-center text-2xl
                ${achievement.isUnlocked ? 'bg-black/20' : 'bg-slate-800'}
              `}>
                {achievement.isUnlocked ? achievement.icon : <Lock size={20} className="text-slate-600" />}
              </div>
              
              <div className="flex-1">
                <h3 className={`font-bold ${achievement.isUnlocked ? 'text-white' : 'text-slate-500'}`}>
                  {achievement.title}
                </h3>
                <p className="text-sm text-slate-400">
                  {achievement.description}
                </p>
              </div>

              {achievement.isUnlocked && (
                <div className="px-3 py-1 rounded-full text-xs font-bold uppercase tracking-widest bg-black/30 border border-white/10">
                  Unlocked
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default AchievementsMenu;
