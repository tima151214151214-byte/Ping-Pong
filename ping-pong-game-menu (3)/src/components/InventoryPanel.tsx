import React from 'react';
import { X, Package, Layers, Brush, Sparkles } from 'lucide-react';
import { ArenaTheme, PaddleStyle, BoosterId } from '../types';

interface InventoryPanelProps {
  isOpen: boolean;
  onClose: () => void;
  ownedThemes: ArenaTheme[];
  ownedStyles: PaddleStyle[];
  ownedMapCards: string[];
  ownedBoosters: BoosterId[];
  activeThemeId?: ArenaTheme;
  activeStyleId?: PaddleStyle;
  activeMapCardId?: string;
  activeBoosters?: BoosterId[];
  onSelectTheme?: (theme: ArenaTheme) => void;
  onSelectStyle?: (style: PaddleStyle) => void;
  onSelectMapCard?: (cardId: string) => void;
  onToggleBooster?: (boosterId: BoosterId) => void;
}

const themeLabels: Record<ArenaTheme, string> = {
  NEON: 'Неон',
  CLASSIC: 'Классика',
  GRID: 'Сетка',
  SUNSET: 'Закат',
  ICE: 'Лёд',
  VOID: 'Пустота',
  AUTUMN: 'Осень',
  WINTER: 'Зима',
  ROYAL: 'Королевская'
};

const styleLabels: Record<PaddleStyle, string> = {
  SOLID: 'Солид',
  GLOW: 'Сияние',
  OUTLINE: 'Контур'
};

const boosterLabels: Record<BoosterId, string> = {
  TRAJECTORY: 'Траектория+',
  TRAJECTORY_SUB: 'Траектория PRO',
  SOFT_MAGNET: 'Мягкий магнит',
  SOFT_SLOW: 'Лёгкое замедление',
  STABILITY: 'Стабилизация'
};

const mapCardDescriptions = [
  'Туманная арена с мягким свечением.',
  'Неоновый лабиринт с тонкой сеткой.',
  'Темный ангар в стиле sci‑fi.',
  'Глянцевая арена с отражением света.',
  'Трасса с пульсирующими линиями.',
  'Минимализм и холодные оттенки.'
];

const getMapCardLabel = (cardId: string) => {
  const index = Number(cardId.split('_')[1] || 0);
  if (!index) return 'Карта';
  return `Карта #${index}`;
};

const getMapCardDescription = (cardId: string) => {
  const index = Number(cardId.split('_')[1] || 1);
  return mapCardDescriptions[(index - 1) % mapCardDescriptions.length];
};

export const InventoryPanel: React.FC<InventoryPanelProps> = ({
  isOpen,
  onClose,
  ownedThemes,
  ownedStyles,
  ownedMapCards,
  ownedBoosters,
  activeThemeId,
  activeStyleId,
  activeMapCardId,
  activeBoosters = [],
  onSelectTheme,
  onSelectStyle,
  onSelectMapCard,
  onToggleBooster
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[120] bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="w-full max-w-4xl h-[85vh] bg-slate-950 border border-cyan-500/20 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b border-slate-800 bg-slate-900">
          <div className="flex items-center gap-3">
            <Package className="text-cyan-400" size={20} />
            <span className="font-bold text-cyan-300 uppercase tracking-widest">МОИ ПОКУПКИ</span>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white">
            <X size={20} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-10">
          <div>
            <h3 className="text-white font-bold text-sm uppercase tracking-widest mb-4 flex items-center gap-2">
              <Layers size={16} className="text-cyan-400" /> Арены
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {ownedThemes.map((theme) => (
                <button
                  key={theme}
                  onClick={() => onSelectTheme?.(theme)}
                  className={`p-4 rounded-xl border text-left transition-all ${activeThemeId === theme ? 'border-cyan-400 bg-cyan-500/10' : 'border-slate-800 bg-slate-900/60 hover:border-cyan-500/50'}`}
                >
                  <div className="text-white font-bold">{themeLabels[theme]}</div>
                  <div className="text-slate-400 text-xs">
                    {activeThemeId === theme ? 'Активная арена' : 'Купленная арена'}
                  </div>
                </button>
              ))}
            </div>
          </div>

          <div>
            <h3 className="text-white font-bold text-sm uppercase tracking-widest mb-4 flex items-center gap-2">
              <Brush size={16} className="text-purple-400" /> Стили ракеток
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {ownedStyles.map((style) => (
                <button
                  key={style}
                  onClick={() => onSelectStyle?.(style)}
                  className={`p-4 rounded-xl border text-left transition-all ${activeStyleId === style ? 'border-purple-400 bg-purple-500/10' : 'border-slate-800 bg-slate-900/60 hover:border-purple-500/50'}`}
                >
                  <div className="text-white font-bold">{styleLabels[style]}</div>
                  <div className="text-slate-400 text-xs">
                    {activeStyleId === style ? 'Активный стиль' : 'Купленный стиль'}
                  </div>
                </button>
              ))}
            </div>
          </div>

          <div>
            <h3 className="text-white font-bold text-sm uppercase tracking-widest mb-4 flex items-center gap-2">
              <Layers size={16} className="text-emerald-400" /> Карты (покупки)
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-h-[360px] overflow-y-auto pr-2">
              {ownedMapCards.map((card) => (
                <button
                  key={card}
                  onClick={() => onSelectMapCard?.(card)}
                  className={`p-4 rounded-xl border text-left transition-all ${activeMapCardId === card ? 'border-emerald-400 bg-emerald-500/10' : 'border-slate-800 bg-slate-900/60 hover:border-emerald-500/50'}`}
                >
                  <div className="text-white font-bold">{getMapCardLabel(card)}</div>
                  <div className="text-slate-400 text-xs">{getMapCardDescription(card)}</div>
                  <div className="text-[10px] text-slate-500 mt-1">
                    {activeMapCardId === card ? 'Активная карта' : 'Купленная карта'}
                  </div>
                </button>
              ))}
            </div>
          </div>

          <div>
            <h3 className="text-white font-bold text-sm uppercase tracking-widest mb-4 flex items-center gap-2">
              <Sparkles size={16} className="text-yellow-400" /> Усилители
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {ownedBoosters.map((booster) => {
                const active = activeBoosters.includes(booster);
                return (
                  <button
                    key={booster}
                    onClick={() => onToggleBooster?.(booster)}
                    className={`p-4 rounded-xl border text-left transition-all ${active ? 'border-yellow-400 bg-yellow-500/10' : 'border-slate-800 bg-slate-900/60 hover:border-yellow-500/50'}`}
                  >
                    <div className="text-white font-bold">{boosterLabels[booster]}</div>
                    <div className="text-slate-400 text-xs">
                      {active ? 'Активный усилитель' : 'Купленный усилитель'}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
