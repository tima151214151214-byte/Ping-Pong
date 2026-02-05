import React from 'react';
import { X, ShoppingCart } from 'lucide-react';
import { ArenaTheme, PaddleStyle } from '../types';

interface StorePanelProps {
  isOpen: boolean;
  onClose: () => void;
  coins: number;
  ownedThemes: ArenaTheme[];
  ownedStyles: PaddleStyle[];
  ownedMapCards: string[];
  ownedBoosters: Array<'TRAJECTORY' | 'TRAJECTORY_SUB' | 'SOFT_MAGNET' | 'SOFT_SLOW' | 'STABILITY'>;
  onBuyTheme: (theme: ArenaTheme, price: number) => void;
  onBuyStyle: (style: PaddleStyle, price: number) => void;
  onBuyMapCard: (cardId: string, price: number) => void;
  onBuyBooster: (boosterId: 'TRAJECTORY' | 'TRAJECTORY_SUB' | 'SOFT_MAGNET' | 'SOFT_SLOW' | 'STABILITY', price: number) => void;
}

const themeItems: { id: ArenaTheme; title: string; description: string; price: number }[] = [
  { id: 'NEON', title: 'Неоновая арена', description: 'Яркая неоновая сетка с холодным свечением.', price: 0 },
  { id: 'CLASSIC', title: 'Классика', description: 'Темная минималистичная арена без лишних эффектов.', price: 50 },
  { id: 'GRID', title: 'Сетка', description: 'Кибер‑сетка в стиле тренировочного симулятора.', price: 80 },
  { id: 'SUNSET', title: 'Закат', description: 'Градиентный закат с теплым небом и мягким светом.', price: 120 },
  { id: 'ICE', title: 'Лед', description: 'Холодные тона и ледяная подсветка.', price: 160 },
  { id: 'VOID', title: 'Пустота', description: 'Глубокий космический мрак с фиолетовым свечением.', price: 220 },
];

const styleItems: { id: PaddleStyle; title: string; price: number }[] = [
  { id: 'SOLID', title: 'Солид', price: 20 },
  { id: 'GLOW', title: 'Сияние', price: 40 },
  { id: 'OUTLINE', title: 'Контур', price: 60 },
];

const mapCardDescriptions = [
  'Туманная арена с мягким свечением.',
  'Неоновый лабиринт с тонкой сеткой.',
  'Темный ангар в стиле sci‑fi.',
  'Глянцевая арена с отражением света.',
  'Трасса с пульсирующими линиями.',
  'Минимализм и холодные оттенки.'
];

const mapCards = Array.from({ length: 300 }).map((_, index) => ({
  id: `map_${index + 1}`,
  title: `Карта #${index + 1}`,
  description: mapCardDescriptions[index % mapCardDescriptions.length],
  price: Math.min(500, 20 + index)
}));

const boosters: { id: 'TRAJECTORY' | 'TRAJECTORY_SUB' | 'SOFT_MAGNET' | 'SOFT_SLOW' | 'STABILITY'; title: string; price: number; description: string }[] = [
  { id: 'TRAJECTORY', title: 'Траектория+', price: 30, description: 'Показывает путь мяча на всю арену.' },
  { id: 'TRAJECTORY_SUB', title: 'Траектория PRO (подписка 2 года)', price: 15000, description: 'Постоянная траектория + усиленный прогноз.' },
  { id: 'SOFT_MAGNET', title: 'Мягкий магнит', price: 40, description: 'Лёгкая помощь к мячу (почти незаметно).' },
  { id: 'SOFT_SLOW', title: 'Лёгкое замедление', price: 50, description: 'Мяч слегка теряет скорость возле соперника.' },
  { id: 'STABILITY', title: 'Стабилизация', price: 60, description: 'Уменьшает случайные отскоки.' }
];

export const StorePanel: React.FC<StorePanelProps> = ({
  isOpen,
  onClose,
  coins,
  ownedThemes,
  ownedStyles,
  ownedMapCards,
  ownedBoosters,
  onBuyTheme,
  onBuyStyle,
  onBuyMapCard,
  onBuyBooster
}) => { 
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[120] bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="w-full max-w-4xl h-[85vh] bg-slate-950 border border-emerald-500/20 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b border-slate-800 bg-slate-900">
          <div className="flex items-center gap-3">
            <ShoppingCart className="text-emerald-400" size={20} />
            <span className="font-bold text-emerald-300 uppercase tracking-widest">МАГАЗИН</span>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-emerald-300 font-mono">💰 {coins}</div>
            <button onClick={onClose} className="text-slate-400 hover:text-white">
              <X size={20} />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-10">
          <div>
            <h3 className="text-white font-bold text-sm uppercase tracking-widest mb-4">АРЕНЫ</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {themeItems.map((item) => {
                const owned = ownedThemes.includes(item.id);
                const canBuy = coins >= item.price;
                return (
                  <div key={item.id} className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 flex items-center justify-between gap-4">
                    <div>
                      <div className="text-white font-bold">{item.title}</div>
                      <div className="text-slate-400 text-xs">{item.description}</div>
                      <div className="text-slate-500 text-xs mt-1">Цена: {item.price}</div>
                    </div>
                    <button
                      onClick={() => !owned && onBuyTheme(item.id, item.price)}
                      className={`px-3 py-2 rounded-lg text-xs font-bold ${owned ? 'bg-emerald-500/20 text-emerald-300' : canBuy ? 'bg-emerald-600 text-black' : 'bg-slate-800 text-slate-500'}`}
                      disabled={owned || !canBuy}
                    >
                      {owned ? 'КУПЛЕНО' : 'КУПИТЬ'}
                    </button>
                  </div>
                );
              })}
            </div>
          </div>

          <div>
            <h3 className="text-white font-bold text-sm uppercase tracking-widest mb-4">СТИЛИ РАКЕТОК</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {styleItems.map((item) => {
                const owned = ownedStyles.includes(item.id);
                const canBuy = coins >= item.price;
                return (
                  <div key={item.id} className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 flex items-center justify-between">
                    <div>
                      <div className="text-white font-bold">{item.title}</div>
                      <div className="text-slate-400 text-xs">Цена: {item.price}</div>
                    </div>
                    <button
                      onClick={() => !owned && onBuyStyle(item.id, item.price)}
                      className={`px-3 py-2 rounded-lg text-xs font-bold ${owned ? 'bg-emerald-500/20 text-emerald-300' : canBuy ? 'bg-emerald-600 text-black' : 'bg-slate-800 text-slate-500'}`}
                      disabled={owned || !canBuy}
                    >
                      {owned ? 'КУПЛЕНО' : 'КУПИТЬ'}
                    </button>
                  </div>
                );
              })}
            </div>
          </div>

          <div>
            <h3 className="text-white font-bold text-sm uppercase tracking-widest mb-4">КАРТЫ (300)</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-h-[420px] overflow-y-auto pr-2">
              {mapCards.map((card) => {
                const owned = ownedMapCards.includes(card.id);
                const canBuy = coins >= card.price;
                return (
                  <div key={card.id} className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 flex items-center justify-between gap-4">
                    <div>
                      <div className="text-white font-bold">{card.title}</div>
                      <div className="text-slate-400 text-xs">{card.description}</div>
                      <div className="text-slate-500 text-xs mt-1">Цена: {card.price}</div>
                    </div>
                    <button
                      onClick={() => !owned && onBuyMapCard(card.id, card.price)}
                      className={`px-3 py-2 rounded-lg text-xs font-bold ${owned ? 'bg-emerald-500/20 text-emerald-300' : canBuy ? 'bg-emerald-600 text-black' : 'bg-slate-800 text-slate-500'}`}
                      disabled={owned || !canBuy}
                    >
                      {owned ? 'КУПЛЕНО' : 'КУПИТЬ'}
                    </button>
                  </div>
                );
              })}
            </div>
          </div>

          <div>
            <h3 className="text-white font-bold text-sm uppercase tracking-widest mb-4">УСИЛИТЕЛИ</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {boosters.map((item) => {
                const owned = ownedBoosters.includes(item.id);
                const canBuy = coins >= item.price;
                return (
                  <div key={item.id} className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 flex items-center justify-between">
                    <div>
                      <div className="text-white font-bold">{item.title}</div>
                      <div className="text-slate-400 text-xs">Цена: {item.price}</div>
                    </div>
                    <button
                      onClick={() => !owned && onBuyBooster(item.id, item.price)}
                      className={`px-3 py-2 rounded-lg text-xs font-bold ${owned ? 'bg-emerald-500/20 text-emerald-300' : canBuy ? 'bg-emerald-600 text-black' : 'bg-slate-800 text-slate-500'}`}
                      disabled={owned || !canBuy}
                    >
                      {owned ? 'КУПЛЕНО' : 'КУПИТЬ'}
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
