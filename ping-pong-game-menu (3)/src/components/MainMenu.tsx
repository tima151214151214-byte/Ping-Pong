import React, { useState } from 'react';
import { Bot, Users, Cpu, Zap, Skull, ChevronLeft, Clock, Trophy, MoveHorizontal, Lock, Unlock, LogIn, LogOut, User as UserIcon, Globe, Eye, UserX, ShoppingCart, Calendar, Package, BookOpen } from 'lucide-react';
import { OpponentType, BotDifficulty, GameConfig, WinCondition, User } from '../types';
import { translations, Language } from '../i18n/translations';

interface MainMenuProps {
  onSelect: (opponent: OpponentType, difficulty?: BotDifficulty, config?: GameConfig) => void;
  onUnlockMode: (mode: 'admin' | 'dev' | 'ultra') => void;
  unlockedModes: { admin: boolean; dev: boolean; ultra: boolean };
  onOpenAchievements: () => void;
  currentUser: User | null;
  onLoginClick: () => void;
  onLogout: () => void;
  language: Language;
  setLanguage: (lang: Language) => void;
  onOnlineClick: () => void;
  onSpectate?: () => void;
  isCheatHidden: boolean;
  onToggleCheatHidden: () => void;
  onSetLevel: (level: number) => void;
  playerLevel: number;
  onOpenStore: () => void;
  onOpenTasks: () => void;
  onOpenInventory: () => void;
  onOpenTraining: () => void;
  trainingCompleted: boolean;
}

export const MainMenu: React.FC<MainMenuProps> = ({ 
  onSelect, 
  onUnlockMode, 
  unlockedModes, 
  onOpenAchievements,
  currentUser,
  onLoginClick,
  onLogout,
  language,
  setLanguage,
  onOnlineClick,
  onSpectate,
  isCheatHidden,
  onToggleCheatHidden,
  onSetLevel,
  playerLevel,
  onOpenStore,
  onOpenTasks,
  onOpenInventory,
  onOpenTraining,
  trainingCompleted
}) => {
  const t = translations[language];
  const [step, setStep] = useState<'MODE' | 'DIFFICULTY' | 'CONFIG' | 'SPECTATE_LOBBY'>('MODE');
  const [selectedOpponent, setSelectedOpponent] = useState<OpponentType>('BOT');
  
  // Secret State
  const [isPinOpen, setIsPinOpen] = useState(false);
  const [targetMode, setTargetMode] = useState<'admin' | 'dev' | 'ultra' | null>(null);
  const [pin, setPin] = useState('');
  const [pinError, setPinError] = useState(false);
  const [devAuthStep, setDevAuthStep] = useState<1 | 2>(1); // For 2-step dev auth
  const [ultraAuthStep, setUltraAuthStep] = useState<1 | 2 | 3>(1);
  // Simulated Matches for Spectator
  const [simulatedMatches] = useState(() => {
     return Array.from({ length: 40 }).map((_, i) => {
         const isBot = Math.random() > 0.5;
         const p1 = isBot ? `Bot-${1000+i}` : `Player${Math.floor(Math.random()*9000)+1000}`;
         const p2 = isBot ? `Bot-${2000+i}` : `Player${Math.floor(Math.random()*9000)+1000}`;
         const score1 = Math.floor(Math.random() * 9);
         const score2 = Math.floor(Math.random() * 9);
         return {
             id: i,
             p1, p2,
             score: `${score1} - ${score2}`,
             type: isBot ? 'BOT' : 'ONLINE',
             status: Math.random() > 0.8 ? 'MATCH_POINT' : 'LIVE'
         };
     });
  });

  const handleOpenPin = (mode: 'admin' | 'dev' | 'ultra') => {
    setTargetMode(mode);
    setDevAuthStep(1);
    setUltraAuthStep(1);
    setIsPinOpen(true);
    setPin('');
  };

  const handlePinSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (pin === '151214') {
      if (targetMode === 'dev' && devAuthStep === 1) {
        setDevAuthStep(2);
        setPin('');
        return;
      }
      if (targetMode === 'ultra' && ultraAuthStep < 3) {
        setUltraAuthStep((prev) => (prev + 1) as 1 | 2 | 3);
        setPin('');
        return;
      }

      if (targetMode) onUnlockMode(targetMode);
      setIsPinOpen(false);
      setPin('');
      setTargetMode(null);
      setDevAuthStep(1);
      setUltraAuthStep(1);
    } else {
      setPinError(true);
      setTimeout(() => setPinError(false), 1000);
      if (targetMode === 'ultra') {
        setUltraAuthStep(1);
      }
    }
  };
  const [selectedDifficulty, setSelectedDifficulty] = useState<BotDifficulty>('EASY');
  const [unlockedBotLevels, setUnlockedBotLevels] = useState(false);
  const handleUnlockAllBots = () => setUnlockedBotLevels(true);  
  // Config State
  const [winCondition, setWinCondition] = useState<WinCondition>('SCORE');
  const [winValue, setWinValue] = useState<number>(10);
  const [paddleSize, setPaddleSize] = useState<number>(1.0);
  const [arenaTheme, setArenaTheme] = useState<'NEON' | 'CLASSIC' | 'GRID' | 'SUNSET' | 'ICE' | 'VOID'>('NEON');
  const [paddleStyle, setPaddleStyle] = useState<'SOLID' | 'GLOW' | 'OUTLINE'>('GLOW');
  const themeLabels: Record<string, string> = {
    NEON: t.neon,
    CLASSIC: t.classic,
    GRID: t.themeGrid,
    SUNSET: t.themeSunset,
    ICE: t.themeIce,
    VOID: t.themeVoid
  };

  const handleModeSelect = (opp: OpponentType) => {
    setSelectedOpponent(opp);
    if (opp === 'BOT') {
      setStep('DIFFICULTY');
    } else {
      setStep('CONFIG');
    }
  };

  const handleDifficultySelect = (diff: BotDifficulty) => {
    setSelectedDifficulty(diff);
    setStep('CONFIG');
  };

  const canSelectDifficulty = (difficulty: BotDifficulty) => {
    if (unlockedModes.dev) return true;
    if (unlockedBotLevels) return true;
    if (!trainingCompleted) return difficulty === 'EASY';
    if (difficulty === 'EASY' || difficulty === 'NORMAL') return true;
    return false;
  };

  const handleStartGame = () => {
    onSelect(selectedOpponent, selectedOpponent === 'BOT' ? selectedDifficulty : undefined, {
      winCondition,
      winValue,
      paddleSizeMultiplier: paddleSize,
      arenaTheme,
      paddleStyle,
    });
  };

  const ConfigScreen = () => (
    <div className="flex flex-col items-center justify-center space-y-8 animate-in fade-in slide-in-from-right-10 duration-300 w-full max-w-md mx-auto p-4 overflow-y-auto max-h-[90vh]">
       <button 
          onClick={() => setStep(selectedOpponent === 'BOT' ? 'DIFFICULTY' : 'MODE')}
          className="self-start flex items-center gap-2 text-slate-500 hover:text-white transition-colors mb-2 font-mono"
        >
          <ChevronLeft size={20} /> BACK
        </button>

        <h2 className="text-3xl font-bold text-white mb-2 uppercase tracking-widest drop-shadow-glow text-center">
          {t.gameConfig}
        </h2>

        {/* Win Condition */}
        <div className="w-full space-y-4">
          <label className="text-slate-400 text-xs font-bold tracking-widest uppercase">{t.winCondition}</label>
          <div className="flex bg-slate-900 p-1 rounded-xl border border-slate-800">
            <button
              onClick={() => { setWinCondition('SCORE'); setWinValue(10); }}
              className={`flex-1 py-3 rounded-lg flex items-center justify-center gap-2 font-bold transition-all ${
                winCondition === 'SCORE' ? 'bg-slate-700 text-white shadow-lg' : 'text-slate-500 hover:text-slate-300'
              }`}
            >
              <Trophy size={18} /> {t.score}
            </button>
            <button
              onClick={() => { setWinCondition('TIME'); setWinValue(60); }}
              className={`flex-1 py-3 rounded-lg flex items-center justify-center gap-2 font-bold transition-all ${
                winCondition === 'TIME' ? 'bg-slate-700 text-white shadow-lg' : 'text-slate-500 hover:text-slate-300'
              }`}
            >
              <Clock size={18} /> {t.time}
            </button>
          </div>

          {/* Value Slider */}
          <div className="bg-slate-900/50 p-4 rounded-xl border border-slate-800 space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-slate-300 font-bold">
                {winCondition === 'SCORE' ? t.targetScore : t.targetTime}
              </span>
              <span className="text-cyan-400 font-mono text-xl font-bold">
                {winValue} {winCondition === 'SCORE' ? '' : 's'}
              </span>
            </div>
            <input
              type="range"
              min={winCondition === 'SCORE' ? 1 : 30}
              max={winCondition === 'SCORE' ? 100 : 300}
              step={winCondition === 'SCORE' ? 1 : 10}
              value={winValue}
              onChange={(e) => setWinValue(Number(e.target.value))}
              className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-cyan-500"
            />
          </div>
        </div>

        <div className="w-full space-y-4">
          <label className="text-slate-400 text-xs font-bold tracking-widest uppercase flex items-center gap-2">
            <MoveHorizontal size={14} /> {t.paddleSize}
          </label>
          <div className="bg-slate-900/50 p-4 rounded-xl border border-slate-800 space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-slate-300 font-bold">Multiplier</span>
              <span className="text-purple-400 font-mono text-xl font-bold">x{paddleSize.toFixed(1)}</span>
            </div>
            <input
              type="range"
              min="1.0"
              max="1.5"
              step="0.1"
              value={paddleSize}
              onChange={(e) => setPaddleSize(Number(e.target.value))}
              className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-purple-500"
            />
          </div>
        </div>

        <div className="w-full space-y-4">
          <label className="text-slate-400 text-xs font-bold tracking-widest uppercase">{t.arenaTheme}</label>
          <div className="grid grid-cols-3 gap-2">
            {(['NEON', 'CLASSIC', 'GRID', 'SUNSET', 'ICE', 'VOID'] as const).map((theme) => (
              <button
                key={theme}
                onClick={() => setArenaTheme(theme)}
                className={`py-2 rounded-lg font-bold ${arenaTheme === theme ? 'bg-cyan-600 text-white' : 'bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-white'}`}
              >
                {themeLabels[theme]}
              </button>
            ))}
          </div>
        </div>

        <div className="w-full space-y-4">
          <label className="text-slate-400 text-xs font-bold tracking-widest uppercase">Стиль ракеток</label>
          <div className="grid grid-cols-3 gap-2">
            {['SOLID', 'GLOW', 'OUTLINE'].map((style) => (
              <button
                key={style}
                onClick={() => setPaddleStyle(style as 'SOLID' | 'GLOW' | 'OUTLINE')}
                className={`py-2 rounded-lg font-bold ${paddleStyle === style ? 'bg-purple-600 text-white' : 'bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-white'}`}
              >
                {style}
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={handleStartGame}
          className="w-full py-4 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 text-white font-black text-xl hover:scale-105 transition-transform shadow-[0_0_30px_-5px_rgba(6,182,212,0.5)]"
        >
          {t.startGame}
        </button>
    </div>
  );

  const SpectateLobby = () => (
      <div className="flex flex-col items-center justify-center w-full max-w-4xl mx-auto p-4 h-[80vh]">
         <div className="flex items-center justify-between w-full mb-6">
             <button 
                onClick={() => setStep('MODE')}
                className="flex items-center gap-2 text-slate-500 hover:text-white transition-colors font-mono"
              >
                <ChevronLeft size={20} /> BACK
              </button>
              <h2 className="text-2xl font-black text-white uppercase tracking-widest drop-shadow-glow flex items-center gap-2">
                 <Eye size={24} className="text-red-500" />
                 {t.liveMatches}
                 <span className="text-xs bg-red-600 text-white px-2 py-0.5 rounded animate-pulse">LIVE</span>
              </h2>
              <div className="w-20" /> {/* Spacer */}
         </div>

         <div className="w-full flex-1 overflow-y-auto pr-2 space-y-2">
             {simulatedMatches.map(match => (
                 <button 
                    key={match.id}
                    onClick={onSpectate}
                    className="w-full flex items-center justify-between p-4 bg-slate-900/50 border border-slate-800 rounded-xl hover:bg-slate-800 hover:border-cyan-500/50 transition-all group"
                 >
                    <div className="flex items-center gap-4">
                        <div className={`p-2 rounded-lg ${match.type === 'BOT' ? 'bg-slate-800 text-purple-400' : 'bg-blue-900/20 text-blue-400'}`}>
                           {match.type === 'BOT' ? <Bot size={18} /> : <Globe size={18} />}
                        </div>
                        <div className="text-left">
                            <div className="font-bold text-slate-300 text-sm">{match.p1} <span className="text-slate-600 mx-1">vs</span> {match.p2}</div>
                            <div className="text-xs text-slate-500 font-mono mt-0.5">
                               {match.type === 'BOT' ? t.botMatch : t.ranked} • ID: #{match.id + 4200}
                            </div>
                        </div>
                    </div>

                    <div className="flex items-center gap-6">
                        <div className="font-mono text-xl font-bold text-white tracking-widest">
                            {match.score}
                        </div>
                        <div className={`px-2 py-1 rounded text-[10px] font-bold uppercase tracking-wider ${match.status === 'MATCH_POINT' ? 'bg-red-500/20 text-red-500 animate-pulse' : 'bg-green-500/20 text-green-500'}`}>
                            {match.status === 'MATCH_POINT' ? t.matchPoint : t.live}
                        </div>
                    </div>
                 </button>
             ))}
         </div>
      </div>
  );

  if (step === 'SPECTATE_LOBBY') {
      return <SpectateLobby />;
  }

  if (step === 'CONFIG') {
    return <ConfigScreen />;
  }

  if (step === 'DIFFICULTY') {
    return (
      <div className="flex flex-col items-center justify-center space-y-8 animate-in fade-in zoom-in duration-300 w-full max-w-md mx-auto p-4">
        <button 
          onClick={() => setStep('MODE')}
          className="self-start flex items-center gap-2 text-slate-500 hover:text-white transition-colors mb-4 font-mono"
        >
          <ChevronLeft size={20} /> BACK
        </button>

        <h2 className="text-3xl font-bold text-white mb-6 uppercase tracking-widest drop-shadow-glow">{t.selectDifficulty}</h2>
        
        <div className="flex flex-col gap-3 w-full">
          {!unlockedBotLevels && !unlockedModes.dev && (
            <button
              onClick={handleUnlockAllBots}
              className="w-full py-2 rounded-xl bg-slate-800 text-slate-300 border border-slate-700 hover:border-cyan-400 hover:text-cyan-300 transition-all text-xs uppercase tracking-widest"
            >
              {t.unlockAllLevels}
            </button>
          )}
          {[{ id: 'EASY', label: t.easy, icon: <Zap size={24} />, color: 'green' },
            { id: 'NORMAL', label: 'NORMAL', icon: <Cpu size={24} />, color: 'cyan' },
            { id: 'ADAPTIVE', label: t.medium, icon: <Cpu size={24} />, color: 'cyan' },
            { id: 'HARD', label: 'HARD', icon: <Skull size={24} />, color: 'red' },
            { id: 'EXPERT', label: 'EXPERT', icon: <Skull size={24} />, color: 'red' },
            { id: 'MASTER', label: 'MASTER', icon: <Skull size={24} />, color: 'red' },
            { id: 'NIGHTMARE', label: 'NIGHTMARE', icon: <Skull size={24} />, color: 'red' },
            { id: 'IMPOSSIBLE', label: t.impossible, icon: <Skull size={24} />, color: 'red' }
          ].map((diff) => {
            const allowed = canSelectDifficulty(diff.id as BotDifficulty);
            return (
              <button
                key={diff.id}
                onClick={() => allowed && handleDifficultySelect(diff.id as BotDifficulty)}
                className={`group relative flex items-center gap-4 p-4 rounded-xl border transition-all overflow-hidden ${
                  allowed
                    ? 'bg-slate-900/50 border-slate-800 hover:bg-slate-800'
                    : 'bg-slate-950 border-slate-900 opacity-40 cursor-not-allowed'
                }`}
              >
                <div className={`absolute inset-0 ${allowed ? `bg-${diff.color}-500/5 translate-x-[-100%] group-hover:translate-x-0` : ''} transition-transform duration-500`} />
                <div className={`p-3 rounded-full bg-slate-800 text-${diff.color}-500 transition-colors`}>
                  {diff.icon}
                </div>
                <div className="text-left">
                  <div className={`text-lg font-bold ${allowed ? 'text-white' : 'text-slate-500'}`}>{diff.label}</div>
                  {!allowed && <div className="text-xs text-slate-600">LOCKED</div>}
                </div>
              </button>
            );
          })}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center space-y-8 animate-in fade-in zoom-in duration-500 p-4 max-h-screen overflow-y-auto">
      {/* Top Bar: Lang & Profile */}
      <div className="absolute top-4 right-4 z-50 flex items-center gap-3">
        {/* Language Switch */}
        <button
          onClick={() => setLanguage(language === 'ru' ? 'en' : 'ru')}
          className="p-2 bg-slate-900/80 border border-slate-700 rounded-full text-slate-400 hover:text-white transition-colors flex items-center gap-2"
          title="Switch Language"
        >
          <Globe size={18} />
          <span className="text-xs font-bold uppercase">{language}</span>
        </button>

        {/* Profile */}
        {currentUser ? (
          <div className="flex items-center gap-3 bg-slate-900/80 border border-slate-700 p-2 pr-4 rounded-full animate-in fade-in slide-in-from-top-4">
             <div className="w-10 h-10 rounded-full bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-white font-bold shadow-lg">
                <UserIcon size={20} />
             </div>
             <div className="flex flex-col items-start mr-2">
                <span className="text-xs text-slate-400 font-bold uppercase tracking-wider">Player</span>
                <span className="text-white font-bold text-sm">{currentUser.username}</span>
                <span className="text-[10px] text-emerald-400 font-mono">LVL {playerLevel}</span>
             </div>
             <button 
               onClick={onLogout}
               className="p-2 hover:bg-slate-700 rounded-full text-slate-400 hover:text-red-400 transition-colors"
               title={t.logout}
             >
               <LogOut size={18} />
             </button>
          </div>
        ) : (
          <div className="flex flex-col items-end gap-1">
             <button
              onClick={onLoginClick}
              className="group flex items-center gap-2 px-4 py-2 bg-slate-900/80 border border-slate-700 rounded-full hover:border-cyan-500 hover:text-cyan-400 transition-all animate-in fade-in slide-in-from-top-4"
            >
              <LogIn size={18} />
              <span className="font-bold text-sm">{t.loginRegister}</span>
            </button>
            <div className="text-[10px] text-gray-500 font-mono bg-black/50 px-2 py-0.5 rounded flex items-center gap-1 animate-pulse">
               <UserX size={10} /> {t.incognito}
            </div>
          </div>
        )}
      </div>

      <div className="text-center space-y-4 pt-12 md:pt-0">
        <h1 className="text-5xl md:text-7xl font-black italic tracking-tighter text-transparent bg-clip-text bg-gradient-to-br from-cyan-400 via-white to-purple-400 drop-shadow-[0_0_20px_rgba(255,255,255,0.3)]">
          NEON PONG
        </h1>
        <p className="text-slate-400 text-sm md:text-base tracking-[0.3em] uppercase">Cyberpunk Edition</p>
      </div>

      <div className="grid grid-cols-1 gap-4 w-full max-w-md">
        <button
          onClick={() => handleModeSelect('BOT')}
          className="group relative flex items-center p-6 rounded-2xl bg-slate-900 border border-slate-800 hover:border-cyan-500/50 hover:bg-slate-800/80 transition-all duration-300 hover:shadow-[0_0_30px_-5px_rgba(6,182,212,0.3)] overflow-hidden"
        >
           <div className="absolute top-0 right-0 p-3 opacity-10 group-hover:opacity-20 transition-opacity">
             <Bot size={80} />
           </div>
           <div className="relative z-10 flex items-center gap-6">
             <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-cyan-500 group-hover:scale-110 transition-transform">
               <Bot size={32} />
             </div>
             <div className="text-left">
               <h2 className="text-2xl font-bold text-white mb-1 group-hover:text-cyan-400 transition-colors">{t.playBot}</h2>
               <p className="text-slate-500 text-sm">VS AI</p>
             </div>
           </div>
        </button>

        <button
          onClick={() => handleModeSelect('FRIEND')}
          className="group relative flex items-center p-6 rounded-2xl bg-slate-900 border border-slate-800 hover:border-purple-500/50 hover:bg-slate-800/80 transition-all duration-300 hover:shadow-[0_0_30px_-5px_rgba(168,85,247,0.3)] overflow-hidden"
        >
           <div className="absolute top-0 right-0 p-3 opacity-10 group-hover:opacity-20 transition-opacity">
             <Users size={80} />
           </div>
           <div className="relative z-10 flex items-center gap-6">
             <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-purple-500 group-hover:scale-110 transition-transform">
               <Users size={32} />
             </div>
             <div className="text-left">
               <h2 className="text-2xl font-bold text-white mb-1 group-hover:text-purple-400 transition-colors">{t.playFriend}</h2>
               <p className="text-slate-500 text-sm">Local 1v1</p>
             </div>
           </div>
        </button>

        {/* Online Button */}
        <button
          onClick={onOnlineClick}
          className="group relative flex items-center p-6 rounded-2xl bg-slate-900 border border-slate-800 hover:border-blue-500/50 hover:bg-slate-800/80 transition-all duration-300 hover:shadow-[0_0_30px_-5px_rgba(59,130,246,0.3)] overflow-hidden"
        >
           <div className="absolute top-0 right-0 p-3 opacity-10 group-hover:opacity-20 transition-opacity">
             <Globe size={80} />
           </div>
           <div className="relative z-10 flex items-center gap-6">
             <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-blue-500 group-hover:scale-110 transition-transform">
               <Globe size={32} />
             </div>
             <div className="text-left">
               <h2 className="text-2xl font-bold text-white mb-1 group-hover:text-blue-400 transition-colors">{t.playOnline}</h2>
               <p className="text-slate-500 text-sm">{currentUser ? 'Lobby' : t.incognito}</p>
             </div>
           </div>
           {!currentUser && (
               <div className="absolute top-2 right-2 bg-red-500/20 border border-red-500 text-red-400 text-[10px] font-bold px-2 py-0.5 rounded animate-pulse">
                   LOCKED
               </div>
           )}
        </button>

        <div className="grid grid-cols-2 gap-4">
             <button
              onClick={() => setStep('SPECTATE_LOBBY')}
              className="group relative flex items-center p-4 rounded-xl bg-slate-900/50 border border-slate-800 hover:border-indigo-500/50 hover:bg-slate-800/80 transition-all overflow-hidden"
            >
               <div className="relative z-10 flex items-center gap-3 w-full justify-center">
                 <Eye size={20} className="text-indigo-400 group-hover:scale-110 transition-transform" />
                 <span className="text-sm font-bold text-slate-300 group-hover:text-indigo-300 transition-colors">
                   {t.spectate}
                 </span>
               </div>
            </button>

            <button
              onClick={onOpenAchievements}
              className="group relative flex items-center p-4 rounded-xl bg-slate-900/50 border border-slate-800 hover:border-yellow-500/50 hover:bg-slate-800/80 transition-all overflow-hidden"
            >
               <div className="relative z-10 flex items-center gap-3 w-full justify-center">
                 <Trophy size={20} className="text-yellow-500 group-hover:scale-110 transition-transform" />
                 <span className="text-sm font-bold text-slate-300 group-hover:text-yellow-400 transition-colors">
                   {t.achievements}
                 </span>
               </div>
            </button>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <button
            onClick={onOpenStore}
            className="group relative flex items-center p-4 rounded-xl bg-slate-900/50 border border-slate-800 hover:border-emerald-500/50 hover:bg-slate-800/80 transition-all overflow-hidden"
          >
             <div className="relative z-10 flex items-center gap-3 w-full justify-center">
               <ShoppingCart size={20} className="text-emerald-400 group-hover:scale-110 transition-transform" />
               <span className="text-sm font-bold text-slate-300 group-hover:text-emerald-300 transition-colors">
                 {t.store}
               </span>
             </div>
          </button>

          <button
            onClick={onOpenTasks}
            className="group relative flex items-center p-4 rounded-xl bg-slate-900/50 border border-slate-800 hover:border-emerald-500/50 hover:bg-slate-800/80 transition-all overflow-hidden"
          >
             <div className="relative z-10 flex items-center gap-3 w-full justify-center">
               <Calendar size={20} className="text-emerald-400 group-hover:scale-110 transition-transform" />
               <span className="text-sm font-bold text-slate-300 group-hover:text-emerald-300 transition-colors">
                 {t.tasks}
               </span>
             </div>
          </button>
        </div>

        <button
          onClick={onOpenTraining}
          className="group relative flex items-center p-4 rounded-xl bg-slate-900/50 border border-slate-800 hover:border-cyan-500/50 hover:bg-slate-800/80 transition-all overflow-hidden"
        >
          <div className="relative z-10 flex items-center gap-3 w-full justify-center">
            <BookOpen size={20} className="text-cyan-400 group-hover:scale-110 transition-transform" />
            <span className="text-sm font-bold text-slate-300 group-hover:text-cyan-300 transition-colors">
              ОБУЧЕНИЕ {trainingCompleted ? '✔' : ''}
            </span>
          </div>
        </button>

        <button
          onClick={onOpenInventory}
          className="group relative flex items-center p-4 rounded-xl bg-slate-900/50 border border-slate-800 hover:border-cyan-500/50 hover:bg-slate-800/80 transition-all overflow-hidden"
        >
           <div className="relative z-10 flex items-center gap-3 w-full justify-center">
             <Package size={20} className="text-cyan-400 group-hover:scale-110 transition-transform" />
             <span className="text-sm font-bold text-slate-300 group-hover:text-cyan-300 transition-colors">
               Мои покупки
             </span>
           </div>
        </button>

        {(unlockedModes.admin || unlockedModes.dev) && (
          <div className="mt-4 w-full bg-slate-900/60 border border-slate-800 rounded-xl p-4">
            <div className="text-xs text-slate-400 uppercase tracking-widest mb-2">DEV</div>
            <div className="flex items-center gap-3">
              <input
                type="number"
                value={playerLevel}
                onChange={(e) => onSetLevel(Number(e.target.value))}
                className="w-24 bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white font-mono"
                min={0}
              />
              <button
                onClick={() => onSetLevel(playerLevel + 1)}
                className="px-3 py-2 bg-emerald-600 text-black font-bold rounded-lg"
              >
                +1 LVL
              </button>
              <button
                onClick={() => onSetLevel(0)}
                className="px-3 py-2 bg-slate-700 text-white font-bold rounded-lg"
              >
                RESET
              </button>
            </div>
          </div>
        )}
      </div>
      
      {/* Secret Buttons */}
      <div className="absolute bottom-4 right-4 flex gap-4 items-center">
        {/* Admin Lock (Left) */}
        <button 
          onClick={() => unlockedModes.admin ? null : handleOpenPin('admin')}
          className={`p-2 rounded-full transition-all flex items-center gap-2 ${unlockedModes.admin ? 'text-cyan-500 bg-cyan-500/10 cursor-default' : 'text-slate-700 hover:text-cyan-500 hover:bg-slate-800'}`}
          title="Admin Mode"
        >
          {unlockedModes.admin ? <Unlock size={20} /> : <Lock size={20} />}
          {unlockedModes.admin && <span className="text-xs font-bold hidden md:block">ADMIN</span>}
        </button>

        {/* Dev Lock (Right) */}
        <button 
          onClick={() => unlockedModes.dev ? null : handleOpenPin('dev')}
          className={`p-2 rounded-full transition-all flex items-center gap-2 ${unlockedModes.dev ? 'text-red-500 bg-red-500/10 cursor-default' : 'text-slate-700 hover:text-red-500 hover:bg-slate-800'}`}
          title="Developer Mode"
        >
          {unlockedModes.dev ? <Unlock size={20} /> : <Lock size={20} />}
          {unlockedModes.dev && <span className="text-xs font-bold hidden md:block">DEV</span>}
        </button>

        {/* Ultra Lock (Triple PIN) */}
        <button 
          onClick={() => unlockedModes.ultra ? null : handleOpenPin('ultra')}
          className={`p-2 rounded-full transition-all flex items-center gap-2 ${unlockedModes.ultra ? 'text-yellow-400 bg-yellow-500/10 cursor-default' : 'text-slate-700 hover:text-yellow-400 hover:bg-slate-800'}`}
          title="Ultra Mode"
        >
          {unlockedModes.ultra ? <Unlock size={20} /> : <Lock size={20} />}
          {unlockedModes.ultra && <span className="text-xs font-bold hidden md:block">ULTRA</span>}
        </button>

        {/* Cheat Stealth Toggle */}
        {(unlockedModes.admin || unlockedModes.dev) && (
          <button
            onClick={onToggleCheatHidden}
            className={`p-2 rounded-full transition-all flex items-center gap-2 ${isCheatHidden ? 'text-emerald-400 bg-emerald-500/10' : 'text-slate-500 bg-slate-800/60 hover:text-emerald-300'}`}
            title={isCheatHidden ? 'Читы скрыты' : 'Читы видны'}
          >
            {isCheatHidden ? <Unlock size={20} /> : <Lock size={20} />}
            <span className="text-xs font-bold hidden md:block">STEALTH</span>
          </button>
        )}
      </div>

      {/* PIN Modal */}
      {isPinOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm animate-in fade-in">
          <form onSubmit={handlePinSubmit} className="bg-slate-900 border border-slate-700 p-8 rounded-2xl shadow-2xl flex flex-col items-center gap-4 animate-in zoom-in-95" data-step="1">
             <h3 className={`text-white font-bold tracking-widest uppercase ${targetMode === 'dev' ? 'text-red-500' : targetMode === 'ultra' ? 'text-yellow-400' : 'text-cyan-500'}`}>
               {targetMode === 'dev' 
                 ? (devAuthStep === 1 ? 'DEV ACCESS (1/2)' : 'DEV ACCESS (2/2)') 
                 : targetMode === 'ultra'
                   ? `ULTRA ACCESS (${ultraAuthStep}/3)`
                   : 'ADMIN ACCESS'}
             </h3>
             <input
               type="password"
               value={pin}
               onChange={(e) => setPin(e.target.value)}
               placeholder="PIN"
               maxLength={6}
               autoFocus
               className={`w-40 text-center py-2 bg-slate-950 border rounded text-2xl font-mono tracking-widest focus:outline-none ${pinError ? 'border-red-500 text-red-500' : 'border-slate-700 text-white focus:border-cyan-500'}`}
             />
             <div className="flex gap-2 w-full">
               <button type="button" onClick={() => setIsPinOpen(false)} className="flex-1 py-2 text-slate-400 hover:text-white">Отмена</button>
               <button type="submit" className="flex-1 py-2 bg-slate-800 hover:bg-cyan-600 text-white rounded font-bold transition-colors">Вход</button>
             </div>
          </form>
        </div>
      )}
    </div>
  );
};
