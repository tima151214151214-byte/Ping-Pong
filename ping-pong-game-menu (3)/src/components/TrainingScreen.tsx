import React from 'react';
import { ChevronLeft, CheckCircle, Sparkles } from 'lucide-react';

interface TrainingScreenProps {
  onBack: () => void;
  onComplete: () => void;
  canSkip?: boolean;
  onSkip?: () => void;
}

export const TrainingScreen: React.FC<TrainingScreenProps> = ({ onBack, onComplete, canSkip, onSkip }) => {
  return (
    <div className="flex flex-col items-center justify-center w-full h-full max-h-screen p-6 overflow-y-auto">
      <style>{`
        @keyframes training-ball {
          0% { transform: translateX(0) translateY(0); }
          25% { transform: translateX(120px) translateY(-30px); }
          50% { transform: translateX(240px) translateY(0); }
          75% { transform: translateX(120px) translateY(30px); }
          100% { transform: translateX(0) translateY(0); }
        }
      `}</style>
      <div className="w-full max-w-3xl bg-slate-900/70 border border-slate-800 rounded-3xl p-6 md:p-10 shadow-2xl space-y-8">
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors"
        >
          <ChevronLeft size={20} /> Назад
        </button>

        <div className="text-center space-y-2">
          <h1 className="text-4xl font-black text-white uppercase tracking-widest">Обучение</h1>
          <p className="text-slate-400">Узнай, как играть и пройди базовый курс.</p>
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          <div className="space-y-4">
            <div className="p-4 bg-slate-950/70 border border-slate-800 rounded-2xl">
              <h3 className="text-white font-bold mb-2 flex items-center gap-2"><Sparkles size={16} /> Основы</h3>
              <ul className="text-slate-400 text-sm space-y-1">
                <li>• Двигай ракетку ползунком снизу.</li>
                <li>• Отбивай мяч, не давай ему улететь.</li>
                <li>• Чем выше скорость — тем сложнее отразить.</li>
              </ul>
            </div>
            <div className="p-4 bg-slate-950/70 border border-slate-800 rounded-2xl">
              <h3 className="text-white font-bold mb-2">Фишки</h3>
              <ul className="text-slate-400 text-sm space-y-1">
                <li>• Мяч ускоряется после серии ударов.</li>
                <li>• Отскоки от стен меняют траекторию.</li>
                <li>• Победи, чтобы открыть следующий уровень бота.</li>
              </ul>
            </div>
          </div>

          <div className="flex flex-col items-center justify-center gap-4">
            <div className="w-full max-w-sm h-40 bg-slate-950/70 border border-slate-800 rounded-2xl relative overflow-hidden">
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="h-2 w-full border-t border-slate-700" />
              </div>
              <div
                className="absolute w-4 h-4 rounded-full bg-cyan-400 shadow-[0_0_20px_rgba(34,211,238,0.7)]"
                style={{ left: 20, top: 70, animation: 'training-ball 2.5s ease-in-out infinite' }}
              />
            </div>
            <p className="text-slate-400 text-sm text-center">Пример траектории мяча и отскоков.</p>
          </div>
        </div>

        <div className="space-y-6">
          <div className="p-4 bg-slate-950/70 border border-slate-800 rounded-2xl">
            <h3 className="text-white font-bold mb-2">Шаг 1 — Отбей мяч в центр</h3>
            <p className="text-slate-400 text-sm">Передвигай ракетку так, чтобы мяч попадал в центральную часть ракетки.</p>
          </div>
          <div className="p-4 bg-slate-950/70 border border-slate-800 rounded-2xl">
            <h3 className="text-white font-bold mb-2">Шаг 2 — Контроль траектории</h3>
            <p className="text-slate-400 text-sm">Попробуй менять угол отскока — ближе к краям ракетки мяч летит острее.</p>
          </div>
          <div className="p-4 bg-slate-950/70 border border-slate-800 rounded-2xl">
            <h3 className="text-white font-bold mb-2">Шаг 3 — Скорость</h3>
            <p className="text-slate-400 text-sm">После серии ударов мяч ускоряется. Будь готов заранее.</p>
          </div>
          <div className="p-4 bg-slate-950/70 border border-slate-800 rounded-2xl">
            <h3 className="text-white font-bold mb-2">Тестовый матч</h3>
            <p className="text-slate-400 text-sm">Нажми кнопку ниже — начнётся лёгкий тестовый матч (до 3 очков).</p>
          </div>
        </div>

        <div className="flex flex-col md:flex-row gap-4 items-center justify-between">
          <div className="text-sm text-slate-400">
            После прохождения открывается <span className="text-white font-bold">2-й уровень бота</span>.
          </div>
          <div className="flex flex-wrap gap-3">
            {canSkip && onSkip && (
              <button
                onClick={onSkip}
                className="px-5 py-3 rounded-xl bg-slate-800 text-white font-bold hover:bg-slate-700 transition-transform"
              >
                Пропустить обучение
              </button>
            )}
            <button
              onClick={onComplete}
              className="px-6 py-3 rounded-xl bg-emerald-500 text-black font-black flex items-center gap-2 hover:scale-105 transition-transform"
            >
              <CheckCircle size={18} /> Начать тестовый матч
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
