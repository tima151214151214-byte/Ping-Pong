import React, { useMemo, useState, useEffect } from 'react';
import { X, Calendar, CalendarClock, CalendarDays } from 'lucide-react';
import { Language } from '../i18n/translations';
import { translations } from '../i18n/translations';

interface TaskItem {
  id: string;
  title: string;
  reward: number;
  type: 'daily' | 'weekly' | 'monthly';
  requirements?: {
    wins?: number;
    games?: number;
    score?: number;
  };
}

interface TasksPanelProps {
  isOpen: boolean;
  onClose: () => void;
  language: Language;
  coins: number;
  stats?: { totalWins: number; totalScore: number; totalGamesPlayed: number };
  claimedTaskIds: string[];
  onClaim: (taskId: string, reward: number) => void;
}

const tasks: TaskItem[] = [
  { id: 'daily_1', title: 'Сыграй 1 матч', reward: 10, type: 'daily', requirements: { games: 1 } },
  { id: 'daily_2', title: 'Выиграй 1 матч', reward: 15, type: 'daily', requirements: { wins: 1 } },
  { id: 'daily_3', title: 'Набери 20 очков', reward: 20, type: 'daily', requirements: { score: 20 } },
  { id: 'daily_4', title: 'Сыграй 3 матча', reward: 25, type: 'daily', requirements: { games: 3 } },
  { id: 'daily_5', title: 'Выиграй 2 матча', reward: 30, type: 'daily', requirements: { wins: 2 } },
  { id: 'daily_6', title: 'Набери 50 очков', reward: 35, type: 'daily', requirements: { score: 50 } },
  { id: 'daily_7', title: 'Выиграй у Бота', reward: 40, type: 'daily', requirements: { wins: 1 } },
  { id: 'daily_8', title: 'Сыграй 5 матчей', reward: 45, type: 'daily', requirements: { games: 5 } },
  { id: 'daily_9', title: 'Выиграй 3 матча', reward: 50, type: 'daily', requirements: { wins: 3 } },
  { id: 'daily_10', title: 'Набери 100 очков', reward: 60, type: 'daily', requirements: { score: 100 } },
  { id: 'daily_11', title: 'Сыграй 7 матчей', reward: 70, type: 'daily', requirements: { games: 7 } },
  { id: 'daily_12', title: 'Выиграй 5 матчей', reward: 80, type: 'daily', requirements: { wins: 5 } },
  { id: 'daily_13', title: 'Набери 150 очков', reward: 90, type: 'daily', requirements: { score: 150 } },
  { id: 'daily_14', title: 'Выиграй у Невозможного', reward: 110, type: 'daily', requirements: { wins: 1 } },
  { id: 'daily_15', title: 'Сыграй 10 матчей', reward: 130, type: 'daily', requirements: { games: 10 } },
  { id: 'daily_16', title: 'Выиграй 8 матчей', reward: 150, type: 'daily', requirements: { wins: 8 } },
  { id: 'daily_17', title: 'Набери 250 очков', reward: 170, type: 'daily', requirements: { score: 250 } },
  { id: 'daily_18', title: 'Выиграй 10 матчей', reward: 200, type: 'daily', requirements: { wins: 10 } },
  { id: 'daily_19', title: 'Набери 300 очков', reward: 220, type: 'daily', requirements: { score: 300 } },
  { id: 'daily_20', title: 'Выиграй 12 матчей', reward: 250, type: 'daily', requirements: { wins: 12 } },
  { id: 'weekly_1', title: 'Сыграй 10 матчей', reward: 120, type: 'weekly', requirements: { games: 10 } },
  { id: 'weekly_2', title: 'Выиграй 7 матчей', reward: 160, type: 'weekly', requirements: { wins: 7 } },
  { id: 'weekly_3', title: 'Набери 200 очков', reward: 190, type: 'weekly', requirements: { score: 200 } },
  { id: 'weekly_4', title: 'Сыграй 15 матчей', reward: 230, type: 'weekly', requirements: { games: 15 } },
  { id: 'weekly_5', title: 'Выиграй 10 матчей', reward: 260, type: 'weekly', requirements: { wins: 10 } },
  { id: 'weekly_6', title: 'Набери 300 очков', reward: 300, type: 'weekly', requirements: { score: 300 } },
  { id: 'weekly_7', title: 'Сыграй 20 матчей', reward: 340, type: 'weekly', requirements: { games: 20 } },
  { id: 'weekly_8', title: 'Выиграй 15 матчей', reward: 380, type: 'weekly', requirements: { wins: 15 } },
  { id: 'weekly_9', title: 'Набери 400 очков', reward: 420, type: 'weekly', requirements: { score: 400 } },
  { id: 'weekly_10', title: 'Победи 3 уровня сложности', reward: 500, type: 'weekly', requirements: { wins: 3 } },
  { id: 'monthly_1', title: 'Сыграй 30 матчей', reward: 600, type: 'monthly', requirements: { games: 30 } },
  { id: 'monthly_2', title: 'Выиграй 25 матчей', reward: 800, type: 'monthly', requirements: { wins: 25 } },
  { id: 'monthly_3', title: 'Набери 1000 очков', reward: 1000, type: 'monthly', requirements: { score: 1000 } },
  { id: 'monthly_4', title: 'Сыграй 50 матчей', reward: 1200, type: 'monthly', requirements: { games: 50 } },
  { id: 'monthly_5', title: 'Выиграй 40 матчей', reward: 1500, type: 'monthly', requirements: { wins: 40 } },
  { id: 'monthly_6', title: 'Набери 1500 очков', reward: 1800, type: 'monthly', requirements: { score: 1500 } },
  { id: 'monthly_7', title: 'Сыграй 70 матчей', reward: 2000, type: 'monthly', requirements: { games: 70 } },
  { id: 'monthly_8', title: 'Выиграй 60 матчей', reward: 2400, type: 'monthly', requirements: { wins: 60 } },
  { id: 'monthly_9', title: 'Набери 2500 очков', reward: 2800, type: 'monthly', requirements: { score: 2500 } },
  { id: 'monthly_10', title: 'Победи в Невозможном 5 раз', reward: 3200, type: 'monthly', requirements: { wins: 5 } }
];

const getLastReset = (type: 'daily' | 'weekly' | 'monthly') => {
  const now = new Date();
  if (type === 'daily') {
    return new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  }
  if (type === 'weekly') {
    const day = now.getDay();
    const diff = now.getDate() - day + (day === 0 ? -6 : 1);
    return new Date(now.getFullYear(), now.getMonth(), diff).getTime();
  }
  return new Date(now.getFullYear(), now.getMonth(), 1).getTime();
};

export const TasksPanel: React.FC<TasksPanelProps> = ({
  isOpen,
  onClose,
  language,
  coins,
  stats,
  claimedTaskIds,
  onClaim
}) => {
  const t = translations[language];
  const [activeTab, setActiveTab] = useState<'daily' | 'weekly' | 'monthly'>('daily');

  const resetKeys = useMemo(() => ({
    daily: getLastReset('daily'),
    weekly: getLastReset('weekly'),
    monthly: getLastReset('monthly')
  }), []);

  useEffect(() => {
    const handleMidnight = () => {
      const now = new Date();
      const next = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1).getTime();
      const delay = next - now.getTime();
      const timer = setTimeout(() => window.location.reload(), delay + 500);
      return () => clearTimeout(timer);
    };
    handleMidnight();
  }, []);

  if (!isOpen) return null;

  const canClaim = (task: TaskItem) => {
    if (!stats || !task.requirements) return true;
    const { wins, games, score } = task.requirements;
    if (wins !== undefined && stats.totalWins < wins) return false;
    if (games !== undefined && stats.totalGamesPlayed < games) return false;
    if (score !== undefined && stats.totalScore < score) return false;
    return true;
  };

  const isClaimed = (taskId: string, type: 'daily' | 'weekly' | 'monthly') => {
    return claimedTaskIds.includes(`${taskId}_${resetKeys[type]}`);
  };

  const TaskList = ({ type, icon: Icon }: { type: 'daily' | 'weekly' | 'monthly'; icon: any }) => (
    <div className="space-y-3">
      <h3 className="text-white font-bold text-sm uppercase tracking-widest flex items-center gap-2">
        <Icon size={16} className="text-emerald-400" /> {type === 'daily' ? t.dailyTasks : type === 'weekly' ? t.weeklyTasks : t.monthlyTasks}
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {tasks.filter(task => task.type === type).map((task) => {
          const claimed = isClaimed(task.id, type);
          return (
            <div key={task.id} className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 flex items-center justify-between">
              <div>
                <div className="text-white font-bold text-sm">{task.title}</div>
                <div className="text-slate-400 text-xs">+{task.reward} {t.coins}</div>
              </div>
              <button
                onClick={() => !claimed && canClaim(task) && onClaim(`${task.id}_${resetKeys[type]}`, task.reward)}
                disabled={claimed || !canClaim(task)}
                className={`px-3 py-2 rounded-lg text-xs font-bold ${claimed ? 'bg-emerald-500/20 text-emerald-300' : canClaim(task) ? 'bg-emerald-600 text-black hover:bg-emerald-500' : 'bg-slate-800 text-slate-500'}`}
              >
                {claimed ? t.claimed : t.claim}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );

  return (
    <div className="fixed inset-0 z-[120] bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="w-full max-w-4xl h-[85vh] bg-slate-950 border border-emerald-500/20 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b border-slate-800 bg-slate-900">
          <div className="flex items-center gap-3">
            <Calendar className="text-emerald-400" size={20} />
            <span className="font-bold text-emerald-300 uppercase tracking-widest">{t.tasks}</span>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-emerald-300 font-mono">💰 {coins}</div>
            <button onClick={onClose} className="text-slate-400 hover:text-white">
              <X size={20} />
            </button>
          </div>
        </div>

        <div className="flex items-center gap-2 px-6 pt-4">
          {[{ key: 'daily', label: t.dailyTasks }, { key: 'weekly', label: t.weeklyTasks }, { key: 'monthly', label: t.monthlyTasks }].map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key as 'daily' | 'weekly' | 'monthly')}
              className={`px-4 py-2 rounded-lg font-bold text-xs uppercase tracking-widest ${activeTab === tab.key ? 'bg-emerald-500 text-black' : 'bg-slate-800 text-slate-300'}`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          {activeTab === 'daily' && <TaskList type="daily" icon={CalendarDays} />}
          {activeTab === 'weekly' && <TaskList type="weekly" icon={CalendarClock} />}
          {activeTab === 'monthly' && <TaskList type="monthly" icon={Calendar} />}
        </div>
      </div>
    </div>
  );
};
