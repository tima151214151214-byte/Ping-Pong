import React from 'react';
import { X, Skull, Wand2, Sparkles } from 'lucide-react';
import { CheatConfig } from '../types';

interface HackerPanelProps {
  isOpen: boolean;
  onClose: () => void;
  config: CheatConfig;
  onUpdate: (updates: Partial<CheatConfig>) => void;
  onAddCoins: (amount: number) => void;
  onSetCoins: (amount: number) => void;
  onBuyAll: () => void;
}

export const HackerPanel: React.FC<HackerPanelProps> = ({
  isOpen,
  onClose,
  config,
  onUpdate,
  onAddCoins,
  onSetCoins,
  onBuyAll
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[120] bg-black/90 backdrop-blur-xl flex items-center justify-center p-4 animate-in fade-in duration-200">
      <div className="w-full max-w-3xl h-[75vh] bg-slate-950 border border-yellow-500/40 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b border-yellow-500/20 bg-slate-900">
          <div className="flex items-center gap-3">
            <Skull className="text-yellow-400" size={20} />
            <span className="font-mono font-black text-yellow-400 tracking-widest">HACKER CONSOLE</span>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white">
            <X size={20} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          <div className="p-4 rounded-xl border border-yellow-500/30 bg-yellow-500/10">
            <h3 className="text-yellow-300 font-bold text-sm uppercase tracking-widest mb-2">УЛЬТРА-ЧИТ</h3>
            <p className="text-yellow-200/70 text-xs mb-4">
              Максимальная сила. Авто-победа, ускорение уровней, контроль мяча.
            </p>
            <button
              onClick={() => onUpdate({ ultraCheat: !config.ultraCheat })}
              className={`w-full py-3 rounded-xl font-black transition-all ${config.ultraCheat ? 'bg-yellow-400 text-black' : 'bg-slate-800 text-yellow-300 border border-yellow-500/40'}`}
            >
              {config.ultraCheat ? 'ВЫКЛЮЧИТЬ' : 'ВКЛЮЧИТЬ'} УЛЬТРА-ЧИТ
            </button>
          </div>

          <div className="p-4 rounded-xl border border-emerald-500/30 bg-emerald-500/10">
            <h3 className="text-emerald-300 font-bold text-sm uppercase tracking-widest mb-3">МОНЕТЫ</h3>
            <div className="flex flex-wrap gap-2 mb-3">
              {[100, 500, 1000, 5000, 10000].map((amount) => (
                <button
                  key={amount}
                  onClick={() => onAddCoins(amount)}
                  className="px-3 py-2 rounded-lg bg-emerald-600 text-black font-bold text-xs hover:bg-emerald-500"
                >
                  +{amount}
                </button>
              ))}
            </div>
            <div className="flex gap-2">
              <input
                type="number"
                min={0}
                placeholder="Сколько монет"
                className="flex-1 bg-slate-950 border border-emerald-400/40 rounded-lg px-3 py-2 text-white"
                onChange={(e) => onSetCoins(Number(e.target.value) || 0)}
              />
              <button
                onClick={(e) => {
                  const input = (e.currentTarget.previousElementSibling as HTMLInputElement) || null;
                  if (input) onSetCoins(Number(input.value) || 0);
                }}
                className="px-4 py-2 rounded-lg bg-emerald-500 text-black font-bold"
              >
                УСТАНОВИТЬ
              </button>
            </div>
            <button
              onClick={onBuyAll}
              className="mt-4 w-full py-3 rounded-xl bg-yellow-400/90 text-black font-black hover:bg-yellow-300"
            >
              КУПИТЬ ВСЁ БЕСПЛАТНО
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <button
              onClick={() => onUpdate({ autoLevelBoost: !config.autoLevelBoost })}
              className={`p-4 rounded-xl border flex flex-col items-center gap-2 transition-all ${config.autoLevelBoost ? 'bg-emerald-500/20 border-emerald-500 text-emerald-300' : 'bg-slate-900 border-slate-800 text-slate-500 hover:text-emerald-300'}`}
            >
              <Sparkles size={24} />
              <span className="font-bold text-xs uppercase">АВТО-УРОВЕНЬ</span>
            </button>

            <button
              onClick={() => onUpdate({ ballControl: !config.ballControl })}
              className={`p-4 rounded-xl border flex flex-col items-center gap-2 transition-all ${config.ballControl ? 'bg-cyan-500/20 border-cyan-500 text-cyan-300' : 'bg-slate-900 border-slate-800 text-slate-500 hover:text-cyan-300'}`}
            >
              <Wand2 size={24} />
              <span className="font-bold text-xs uppercase">КОНТРОЛЬ МЯЧА</span>
            </button>
          </div>

          <div className="p-4 rounded-xl border border-cyan-500/30 bg-cyan-500/10">
            <h3 className="text-cyan-300 font-bold text-sm uppercase tracking-widest mb-2">ТРАЕКТОРИЯ (настройка)</h3>
            <p className="text-cyan-200/70 text-xs mb-4">
              Показывает путь мяча на несколько отскоков. Можно до 100.
            </p>
            <div className="flex items-center gap-3">
              <input
                type="range"
                min={1}
                max={100}
                step={1}
                value={config.trajectoryCount}
                onChange={(e) => onUpdate({ trajectoryCount: Number(e.target.value) })}
                className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-cyan-400"
              />
              <span className="text-cyan-200 font-mono">x{config.trajectoryCount}</span>
            </div>
            <button
              onClick={() => onUpdate({ trajectoryBoost: !config.trajectoryBoost })}
              className={`mt-4 w-full py-3 rounded-xl font-black transition-all ${config.trajectoryBoost ? 'bg-cyan-400 text-black' : 'bg-slate-800 text-cyan-300 border border-cyan-500/40'}`}
            >
              {config.trajectoryBoost ? 'ВЫКЛЮЧИТЬ' : 'ВКЛЮЧИТЬ'} РАСШИРЕННУЮ ТРАЕКТОРИЮ
            </button>
          </div>

          <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800">
            <label className="text-slate-400 text-xs uppercase tracking-widest">Угол траектории мяча</label>
            <div className="flex items-center gap-3 mt-3">
              <input
                type="range"
                min={-60}
                max={60}
                step={1}
                value={config.ballControlAngle}
                onChange={(e) => onUpdate({ ballControlAngle: Number(e.target.value) })}
                className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-yellow-400"
              />
              <span className="text-yellow-300 font-mono">{config.ballControlAngle}°</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
