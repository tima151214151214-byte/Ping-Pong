import React, { useState, useEffect } from 'react';
import { X, Shield, EyeOff, Crosshair, Crown, FastForward, Activity, Zap, Monitor, PauseOctagon, Ghost } from 'lucide-react';
import { CheatConfig, Achievement } from '../types';
import { translations, Language } from '../i18n/translations';

interface DevPanelProps {
  isOpen: boolean;
  onClose: () => void;
  onMinimize?: () => void;
  onOpenHacker?: () => void;
  config: CheatConfig;
  onUpdate: (config: Partial<CheatConfig>) => void;
  unlockedModes: { admin: boolean; dev: boolean; ultra?: boolean };
  onAddCoins?: (amount: number) => void;
  onSetCoins?: (amount: number) => void;
  // Legacy props kept for compatibility
  onUnlockAllAchievements?: () => void;
  achievements?: Achievement[];
  onToggleAchievement?: (id: string) => void;
  initialTab?: 'ADMIN' | 'DEV';
  language: Language;
}

export const DevPanel: React.FC<DevPanelProps> = ({
  isOpen,
  onClose,
  onMinimize,
  onOpenHacker,
  config,
  onUpdate,
  unlockedModes,
  onAddCoins,
  onSetCoins,
  initialTab = 'ADMIN',
  language
}) => {
  const t = translations[language];
  const [activeTab, setActiveTab] = useState<'ADMIN' | 'DEV'>(initialTab);
  const [scoreInput, setScoreInput] = useState<number>(0);

  useEffect(() => {
    if (isOpen && initialTab) {
      setActiveTab(initialTab);
    }
  }, [isOpen, initialTab]);

  if (!isOpen) return null;

  const TabButton = ({ id, label, icon: Icon, color }: { id: 'ADMIN' | 'DEV', label: string, icon: any, color: string }) => (
    <button
      onClick={() => setActiveTab(id)}
      className={`flex-1 py-3 border-b-2 flex items-center justify-center gap-2 transition-all ${
        activeTab === id 
          ? `border-${color}-500 text-${color}-500 bg-${color}-500/10` 
          : 'border-transparent text-slate-500 hover:text-slate-300'
      }`}
    >
      <Icon size={18} />
      <span className="font-bold hidden md:inline">{label}</span>
    </button>
  );

  return (
    <div className="fixed inset-0 z-[100] bg-black/90 backdrop-blur-xl flex items-center justify-center p-4 animate-in fade-in duration-200">
      <div className="w-full max-w-4xl h-[80vh] bg-slate-950 border border-slate-800 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
        
        {/* Header */}
        <div className="flex justify-between items-center p-4 border-b border-slate-800 bg-slate-900">
           <div className="flex items-center gap-4">
              <span className="font-mono font-bold text-white tracking-widest">{t.systemOverride}</span>
              <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${unlockedModes.dev ? 'bg-red-500 text-black' : 'bg-cyan-500 text-black'}`}>
                {unlockedModes.dev ? t.rootAccess : t.adminAccess}
              </span>
           </div>
           <div className="flex items-center gap-2">
             {onMinimize && (
               <button onClick={onMinimize} className="text-slate-400 hover:text-emerald-300">—</button>
             )}
             <button onClick={onClose}><X className="text-slate-400 hover:text-white" /></button>
           </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-slate-800 bg-slate-925">
           {unlockedModes.admin && <TabButton id="ADMIN" label={t.adminPanel} icon={Shield} color="cyan" />}
           {unlockedModes.dev && <TabButton id="DEV" label={t.devPanel} icon={Activity} color="red" />}
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto touch-pan-y p-6">
          
          {/* ADMIN TAB */}
          {activeTab === 'ADMIN' && unlockedModes.admin && (
            <div className="space-y-8 animate-in slide-in-from-left-4 fade-in duration-300">
               <div className="space-y-4">
                 <h3 className="text-cyan-500 font-bold uppercase tracking-widest text-sm flex items-center gap-2">
                   <Monitor size={16} /> {t.gameSettings}
                 </h3>
                 
                 <div className="bg-slate-900/50 p-4 rounded-xl border border-slate-800 space-y-4">
                   {/* Paddle Size */}
                   <div>
                     <div className="flex justify-between mb-2">
                       <label className="text-slate-300 text-sm font-bold">{t.paddleSizeCheat}</label>
                       <span className="text-cyan-400 font-mono">x{config.paddleSizeMultiplier.toFixed(1)}</span>
                     </div>
                     <input
                       type="range"
                       min="0.5"
                       max="1.5"
                       step="0.1"
                       value={config.paddleSizeMultiplier}
                       onChange={(e) => onUpdate({ paddleSizeMultiplier: Number(e.target.value) })}
                       className="w-full h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-cyan-500"
                     />
                   </div>

                   {/* Aim Assist */}
                   <div className="flex items-center justify-between">
                     <span className="text-slate-300 text-sm font-bold">{t.aimAssist}</span>
                     <button 
                        onClick={() => onUpdate({ showHelpers: !config.showHelpers })}
                        className={`w-12 h-6 rounded-full relative transition-colors ${config.showHelpers ? 'bg-cyan-500' : 'bg-slate-700'}`}
                      >
                        <div className={`absolute top-1 bottom-1 w-4 bg-white rounded-full transition-all ${config.showHelpers ? 'left-7' : 'left-1'}`} />
                      </button>
                   </div>
                 </div>
               </div>

               <div className="space-y-4">
                 <h3 className="text-cyan-500 font-bold uppercase tracking-widest text-sm flex items-center gap-2">
                   <Crosshair size={16} /> {t.scoreManip}
                 </h3>
                 <div className="grid grid-cols-2 gap-4">
                    <button 
                        onClick={() => onUpdate({ pendingAction: { type: 'ADD_SCORE', who: 'me', amount: 1 } })} 
                        className="p-4 bg-slate-800 rounded-xl hover:bg-green-500/20 text-green-400 font-bold border border-slate-700 hover:border-green-500 transition-all"
                    >
                        {t.addMe}
                    </button>
                    <button 
                        onClick={() => onUpdate({ pendingAction: { type: 'ADD_SCORE', who: 'enemy', amount: 1 } })}
                        className="p-4 bg-slate-800 rounded-xl hover:bg-red-500/20 text-red-400 font-bold border border-slate-700 hover:border-red-500 transition-all"
                    >
                        {t.addEnemy}
                    </button>
                 </div>
                 <div className="flex gap-2">
                   <input 
                     type="number" 
                     placeholder={t.setExactScore} 
                     value={scoreInput || ''}
                     onChange={(e) => setScoreInput(Number(e.target.value))}
                     className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-4 text-white focus:border-cyan-500 outline-none"
                   />
                                        <button 
                     onClick={() => onUpdate({ pendingAction: { type: 'ADD_SCORE', who: 'me', amount: scoreInput } })}
                     className="px-6 py-2 bg-cyan-600 hover:bg-cyan-500 text-white font-bold rounded-lg"
                   >
                     {t.add}
                   </button>
                 </div>
               </div>

               {onOpenHacker && unlockedModes.ultra && (
                 <div className="space-y-4">
                   <h3 className="text-cyan-500 font-bold uppercase tracking-widest text-sm flex items-center gap-2">
                     <Zap size={16} /> {t.superAccess}
                   </h3>
                   <button
                     onClick={onOpenHacker}
                     className="w-full py-3 rounded-xl bg-yellow-500/10 text-yellow-300 border border-yellow-500/40 font-bold hover:bg-yellow-500/20 transition-all"
                   >
                     ОТКРЫТЬ ХАКЕР ПАНЕЛЬ
                   </button>
                 </div>
               )}

               {(onAddCoins || onSetCoins) && (
                 <div className="space-y-4">
                   <h3 className="text-cyan-500 font-bold uppercase tracking-widest text-sm flex items-center gap-2">
                     <Zap size={16} /> Монеты
                   </h3>
                   <div className="flex flex-wrap gap-2">
                     {[100, 1000, 5000, 10000].map((amount) => (
                       <button
                         key={amount}
                         onClick={() => onAddCoins?.(amount)}
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
                       onChange={(e) => onSetCoins?.(Number(e.target.value) || 0)}
                     />
                     <button
                       onClick={(e) => {
                         const input = (e.currentTarget.previousElementSibling as HTMLInputElement) || null;
                         if (input && onSetCoins) onSetCoins(Number(input.value) || 0);
                       }}
                       className="px-4 py-2 rounded-lg bg-emerald-500 text-black font-bold"
                     >
                       УСТАНОВИТЬ
                     </button>
                   </div>
                 </div>
               )}

               <div className="space-y-4">
                  <h3 className="text-cyan-500 font-bold uppercase tracking-widest text-sm flex items-center gap-2">
                    <Zap size={16} /> {t.assistFeatures}
                  </h3>
                  <div className="grid grid-cols-2 gap-4">
                     {/* Ghost Hit */}
                     <button
                        onClick={() => onUpdate({ ghostHit: !config.ghostHit })}
                        className={`p-4 rounded-xl border flex flex-col items-center gap-2 transition-all ${config.ghostHit ? 'bg-cyan-500/20 border-cyan-500 text-cyan-400' : 'bg-slate-900 border-slate-800 text-slate-500 hover:text-cyan-400'}`}
                     >
                        <Shield size={24} />
                        <span className="font-bold text-xs uppercase">{t.ghostHit}</span>
                        <span className="text-[10px] text-slate-400">{t.ghostHitDesc}</span>
                     </button>

                     {/* Magnetic Paddle */}
                     <button
                        onClick={() => onUpdate({ magneticPaddle: !config.magneticPaddle })}
                        className={`p-4 rounded-xl border flex flex-col items-center gap-2 transition-all ${config.magneticPaddle ? 'bg-cyan-500/20 border-cyan-500 text-cyan-400' : 'bg-slate-900 border-slate-800 text-slate-500 hover:text-cyan-400'}`}
                     >
                        <Zap size={24} />
                        <span className="font-bold text-xs uppercase">{t.magneticPaddle}</span>
                        <span className="text-[10px] text-slate-400">{t.magneticPaddleDesc}</span>
                     </button>
                  </div>
               </div>
            </div>
          )}

          {/* DEV TAB */}
          {activeTab === 'DEV' && unlockedModes.dev && (
            <div className="space-y-8 animate-in slide-in-from-right-4 fade-in duration-300">
               {/* God Mode */}
               <div className="p-6 rounded-2xl bg-gradient-to-br from-red-900/20 to-slate-900 border border-red-500/30 relative overflow-hidden group">
                 <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                   <Crown size={100} />
                 </div>
                 <div className="relative z-10 flex justify-between items-center">
                   <div>
                     <h2 className="text-2xl font-black text-red-500 italic">{t.godMode}</h2>
                     <p className="text-red-300/60 text-sm">{t.godModeDesc}</p>
                   </div>
                   <button 
                      onClick={() => onUpdate({ autoPlay: !config.autoPlay })}
                      className={`px-6 py-2 rounded-lg font-bold transition-all ${config.autoPlay ? 'bg-red-500 text-black shadow-[0_0_20px_red]' : 'bg-slate-800 text-red-500 border border-red-500/50'}`}
                    >
                      {config.autoPlay ? t.enabled : t.disabled}
                    </button>
                 </div>
               </div>

               {(onAddCoins || onSetCoins) && (
                 <div className="space-y-4">
                   <h3 className="text-red-500 font-bold uppercase tracking-widest text-sm flex items-center gap-2">
                     <Zap size={16} /> Монеты (DEV)
                   </h3>
                   <div className="flex flex-wrap gap-2">
                     {[100, 1000, 5000, 10000].map((amount) => (
                       <button
                         key={amount}
                         onClick={() => onAddCoins?.(amount)}
                         className="px-3 py-2 rounded-lg bg-red-600/90 text-black font-bold text-xs hover:bg-red-500"
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
                       className="flex-1 bg-slate-950 border border-red-500/40 rounded-lg px-3 py-2 text-white"
                       onChange={(e) => onSetCoins?.(Number(e.target.value) || 0)}
                     />
                     <button
                       onClick={(e) => {
                         const input = (e.currentTarget.previousElementSibling as HTMLInputElement) || null;
                         if (input && onSetCoins) onSetCoins(Number(input.value) || 0);
                       }}
                       className="px-4 py-2 rounded-lg bg-red-500 text-black font-bold"
                     >
                       УСТАНОВИТЬ
                     </button>
                   </div>
                 </div>
               )}

               {/* Hacks Grid */}
               <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                 <div className="md:col-span-2 p-4 rounded-xl border border-red-500/30 bg-red-900/10">
                   <h4 className="text-red-400 font-bold text-xs uppercase tracking-widest mb-3">УПРАВЛЕНИЕ БОТОМ</h4>
                   <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                     <div className="bg-slate-900/50 p-4 rounded-xl border border-slate-800 space-y-2">
                       <div className="flex justify-between">
                         <span className="text-slate-300 font-bold">Размер ракетки бота</span>
                         <span className="text-red-300 font-mono">x{config.opponentPaddleMultiplier.toFixed(1)}</span>
                       </div>
                       <input
                         type="range"
                         min="0.5"
                         max="8"
                         step="0.1"
                         value={config.opponentPaddleMultiplier}
                         onChange={(e) => onUpdate({ opponentPaddleMultiplier: Number(e.target.value) })}
                         className="w-full h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-red-500"
                       />
                     </div>

                     <div className="bg-slate-900/50 p-4 rounded-xl border border-slate-800 space-y-2">
                       <div className="flex justify-between">
                         <span className="text-slate-300 font-bold">Размер белого ползунка</span>
                         <span className="text-cyan-300 font-mono">x{config.controlThumbScale?.toFixed(1) ?? 1}</span>
                       </div>
                       <input
                         type="range"
                         min="1"
                         max="8"
                         step="0.5"
                         value={config.controlThumbScale ?? 1}
                         onChange={(e) => onUpdate({ controlThumbScale: Number(e.target.value) })}
                         className="w-full h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-cyan-500"
                       />
                     </div>

                     <button
                       onClick={() => onUpdate({ opponentAutoPlay: !config.opponentAutoPlay })}
                       className={`p-4 rounded-xl border flex flex-col items-center gap-2 transition-all ${config.opponentAutoPlay ? 'bg-emerald-500/20 border-emerald-500 text-emerald-400' : 'bg-slate-900 border-slate-800 text-slate-500 hover:text-emerald-400'}`}
                     >
                       <Crown size={24} />
                       <span className="font-bold text-xs uppercase">БОТ-БОКС (ПОМОЩЬ)</span>
                       <span className="text-[10px] text-center text-slate-400">Помогает игроку</span>
                     </button>
                   </div>
                 </div>
                 
                 {/* Glitch Mode (NEW) */}
                 <button
                   onClick={() => onUpdate({ glitchMode: !config.glitchMode })}
                   className={`p-4 rounded-xl border flex flex-col items-center gap-2 transition-all ${config.glitchMode ? 'bg-purple-500/20 border-purple-500 text-purple-400 animate-pulse' : 'bg-slate-900 border-slate-800 text-slate-500 hover:text-purple-400'}`}
                 >
                   <Ghost size={24} />
                   <span className="font-bold text-xs uppercase">{t.glitchMode}</span>
                   <span className="text-[10px] text-center text-slate-400">{t.glitchModeDesc}</span>
                 </button>

                 {/* Mega Paddle */}
                 <div className="bg-slate-900/50 p-4 rounded-xl border border-slate-800 space-y-2">
                   <div className="flex justify-between">
                     <span className="text-slate-300 font-bold">{t.paddleSizeCheat}</span>
                     <span className="text-purple-400 font-mono">x{config.paddleSizeMultiplier.toFixed(1)}</span>
                   </div>
                   <input
                     type="range"
                     min="0.5"
                     max="20"
                     step="0.5"
                     value={config.paddleSizeMultiplier}
                     onChange={(e) => onUpdate({ paddleSizeMultiplier: Number(e.target.value) })}
                     className="w-full h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-purple-500"
                   />
                 </div>

                 {/* Lag Switch */}
                 <div className="bg-slate-900/50 p-4 rounded-xl border border-slate-800 space-y-2">
                   <div className="flex justify-between">
                     <span className="text-slate-300 font-bold">{t.lagSeverity}</span>
                     <span className="text-orange-400 font-mono">{config.lagSeverity}%</span>
                   </div>
                   <input
                     type="range"
                     min="0"
                     max="100"
                     step="5"
                     value={config.lagSeverity}
                     onChange={(e) => onUpdate({ lagSeverity: Number(e.target.value) })}
                     className="w-full h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-orange-500"
                   />
                 </div>

                 {/* Trajectory Preview */}
                 <button
                   onClick={() => onUpdate({ trajectoryPreview: !config.trajectoryPreview })}
                   className={`p-4 rounded-xl border flex flex-col items-center gap-2 transition-all ${config.trajectoryPreview ? 'bg-cyan-500/20 border-cyan-500 text-cyan-400' : 'bg-slate-900 border-slate-800 text-slate-500 hover:text-cyan-400'}`}
                 >
                   <Activity size={24} />
                   <span className="font-bold text-xs uppercase">ТРАЕКТОРИЯ</span>
                 </button>

                 {/* Trajectory Count */}
                 <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/50 space-y-2">
                   <div className="flex justify-between">
                     <span className="text-slate-300 font-bold">Показать отскоки</span>
                     <span className="text-cyan-300 font-mono">x{config.trajectoryCount}</span>
                   </div>
                   <input
                     type="range"
                     min="1"
                     max="100"
                     step="1"
                     value={config.trajectoryCount}
                     onChange={(e) => onUpdate({ trajectoryCount: Number(e.target.value) })}
                     className="w-full h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-cyan-500"
                   />
                 </div>

                 {/* Trajectory Boost */}
                 <button
                   onClick={() => onUpdate({ trajectoryBoost: !config.trajectoryBoost })}
                   className={`p-4 rounded-xl border flex flex-col items-center gap-2 transition-all ${config.trajectoryBoost ? 'bg-cyan-500/20 border-cyan-500 text-cyan-300' : 'bg-slate-900 border-slate-800 text-slate-500 hover:text-cyan-300'}`}
                 >
                   <Activity size={24} />
                   <span className="font-bold text-xs uppercase">ТРАЕКТОРИЯ+ (расшир.)</span>
                   <span className="text-[10px] text-slate-400">Длиннее и точнее</span>
                 </button>

                 {/* Stealth Assist */}
                 <button
                   onClick={() => onUpdate({ stealthAssist: !config.stealthAssist })}
                   className={`p-4 rounded-xl border flex flex-col items-center gap-2 transition-all ${config.stealthAssist ? 'bg-emerald-500/20 border-emerald-500 text-emerald-400' : 'bg-slate-900 border-slate-800 text-slate-500 hover:text-emerald-400'}`}
                 >
                   <Ghost size={24} />
                   <span className="font-bold text-xs uppercase">НЕЗАМЕТНЫЙ ПОМОЩНИК</span>
                   <span className="text-[10px] text-center text-slate-400">Почти 99% побед</span>
                 </button>

                 {/* Hide Cheat UI */}
                 <button
                   onClick={() => onUpdate({ hideCheatUI: !config.hideCheatUI })}
                   className={`p-4 rounded-xl border flex flex-col items-center gap-2 transition-all ${config.hideCheatUI ? 'bg-slate-700 border-slate-500 text-white' : 'bg-slate-900 border-slate-800 text-slate-500 hover:text-white'}`}
                 >
                   <EyeOff size={24} />
                   <span className="font-bold text-xs uppercase">СКРЫТЬ ИНДИКАТОРЫ</span>
                 </button>

                 {/* Rapid Fire Win */}
                 <button
                   onClick={() => onUpdate({ rapidFire: !config.rapidFire })}
                   className={`p-4 rounded-xl border flex flex-col items-center gap-2 transition-all ${config.rapidFire ? 'bg-yellow-500/20 border-yellow-500 text-yellow-400 animate-pulse' : 'bg-slate-900 border-slate-800 text-slate-500 hover:text-yellow-400'}`}
                 >
                   <Zap size={24} />
                   <span className="font-bold text-xs uppercase">{t.rapidFire}</span>
                 </button>

                 {/* Stop World */}
                 <button
                   onClick={() => onUpdate({ stopWorld: !config.stopWorld })}
                   className={`p-4 rounded-xl border flex flex-col items-center gap-2 transition-all ${config.stopWorld ? 'bg-blue-500/20 border-blue-500 text-blue-400' : 'bg-slate-900 border-slate-800 text-slate-500 hover:text-blue-400'}`}
                 >
                   <PauseOctagon size={24} />
                   <span className="font-bold text-xs uppercase">{t.stopWorld}</span>
                 </button>

                 {/* Invisible Enemy */}
                 <button
                   onClick={() => onUpdate({ invisibleOpponent: !config.invisibleOpponent })}
                   className={`p-4 rounded-xl border flex flex-col items-center gap-2 transition-all ${config.invisibleOpponent ? 'bg-slate-800 border-slate-500 text-white' : 'bg-slate-900 border-slate-800 text-slate-500'}`}
                 >
                   <EyeOff size={24} />
                   <span className="font-bold text-xs uppercase">{t.blindEnemy}</span>
                 </button>

                 {/* Slow Motion */}
                 <button
                   onClick={() => onUpdate({ slowMotion: !config.slowMotion })}
                   className={`p-4 rounded-xl border flex flex-col items-center gap-2 transition-all ${config.slowMotion ? 'bg-green-500/10 border-green-500 text-green-400' : 'bg-slate-900 border-slate-800 text-slate-500'}`}
                 >
                   <FastForward size={24} className={config.slowMotion ? 'rotate-180' : ''} />
                   <span className="font-bold text-xs uppercase">{t.matrixMode}</span>
                 </button>
               </div>

               {/* Serve Target */}
               <div className="pt-6 border-t border-slate-800">
                  <h3 className="text-red-500 font-bold text-sm uppercase mb-4">Подача в начале</h3>
                  <div className="grid grid-cols-3 gap-2 mb-4">
                    {[{ id: 'PLAYER', label: 'К тебе' }, { id: 'OPPONENT', label: 'К нему' }, { id: 'RANDOM', label: 'Случайно' }].map((opt) => (
                      <button
                        key={opt.id}
                        onClick={() => onUpdate({ serveTarget: opt.id as 'PLAYER' | 'OPPONENT' | 'RANDOM' })}
                        className={`py-2 rounded font-bold border ${config.serveTarget === opt.id ? 'bg-emerald-500/20 text-emerald-300 border-emerald-400/40' : 'bg-slate-900/40 text-slate-400 border-slate-800'}`}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
               </div>

               {/* Troll Section */}
               <div className="pt-6 border-t border-slate-800">
                  <h3 className="text-red-500 font-bold text-sm uppercase mb-4">{t.opponentManip}</h3>
                  <div className="grid grid-cols-4 gap-2 mb-4">
                    {[1, 2, 3, 4].map(sec => (
                      <button
                        key={sec}
                        onClick={() => onUpdate({ freezeOpponentUntil: Date.now() + sec * 1000 })}
                        className="py-2 bg-blue-900/30 text-blue-400 border border-blue-800/50 rounded font-bold hover:bg-blue-900/60 transition-colors"
                      >
                        {t.freeze} {sec}s
                      </button>
                    ))}
                  </div>

                  <button
                    onClick={() => onUpdate({ pendingAction: { type: 'FORCE_WIN' } })}
                    className="w-full py-3 bg-gradient-to-r from-red-600 to-orange-600 rounded-xl font-black text-white hover:scale-105 transition-transform shadow-lg shadow-red-900/20"
                  >
                    {t.forceWin}
                  </button>
               </div>
            </div>
          )}
        </div>

      </div>
    </div>
  );
};
