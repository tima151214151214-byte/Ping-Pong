import { useState, useEffect } from 'react';
import { MainMenu } from './components/MainMenu';
import { TeamSelect } from './components/TeamSelect';
import { PongGame } from './components/PongGame';
import { DevPanel } from './components/DevPanel';
import { TrainingScreen } from './components/TrainingScreen';
import { CheatDock } from './components/CheatDock';
import { CongratsModal } from './components/CongratsModal';
import { AuthModal } from './components/AuthModal';
import { LevelChallengeModal } from './components/LevelChallengeModal';
import { HackerPanel } from './components/HackerPanel';
import { StorePanel } from './components/StorePanel';
import { TasksPanel } from './components/TasksPanel';
import { InventoryPanel } from './components/InventoryPanel';
import { GameMode, OpponentType, PlayerSide, BotDifficulty, GameConfig, Achievement, GameStats, CheatConfig, User } from './types';
import { generateAchievements } from './data/achievements';
import AchievementsMenu from './components/AchievementsMenu';
import { AuthService } from './services/auth';
import { Language } from './i18n/translations';
import { OnlineLobby } from './components/OnlineLobby';
import { MultiplayerRole } from './types';

const getResetKey = (type: 'daily' | 'weekly' | 'monthly') => {
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

export function App() {
  const [language, setLanguage] = useState<Language>('ru');
  const [mode, setMode] = useState<GameMode | 'ONLINE_LOBBY' | 'TRAINING'>('MENU');
  const [multiplayerRole, setMultiplayerRole] = useState<MultiplayerRole>('NONE');
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  // Helper to merge saved IDs with full achievement objects
  const mergeAchievements = (savedIds: string[]) => {
      const defaults = generateAchievements();
      return defaults.map(def => ({
          ...def,
          isUnlocked: savedIds.includes(def.id)
      }));
  };
  
  // Achievements State
  const [achievements, setAchievements] = useState<Achievement[]>(() => {
    // 1. Try to load logged in user first (synchronous check)
    const user = AuthService.getCurrentUser();
    if (user) {
        return mergeAchievements(user.achievements);
    }
    // 2. Fallback to anonymous local storage
    const saved = localStorage.getItem('neon_pong_achievements');
    const defaults = generateAchievements();
    if (saved) {
        const parsed = JSON.parse(saved) as Achievement[];
        const merged = defaults.map(def => {
            const found = parsed.find(p => p.id === def.id);
            return found ? { ...def, isUnlocked: found.isUnlocked } : def;
        });
        return merged;
    }
    return defaults;
  });
  
  const [stats, setStats] = useState<GameStats>(() => {
    const user = AuthService.getCurrentUser();
    if (user) return { ...user.stats, coins: user.stats.coins ?? 0 };

    const saved = localStorage.getItem('neon_pong_stats');
    return saved ? JSON.parse(saved) : { totalWins: 0, totalLosses: 0, totalExits: 0, totalGamesPlayed: 0, totalScore: 0, maxRally: 0, level: 0, coins: 0, unlockedThemeIds: ['NEON'], unlockedStyleIds: ['GLOW'], activeThemeId: 'NEON', activeStyleId: 'GLOW', activeMapCardId: 'default', activeBoosters: [] };
  });

  const [ownedThemes, setOwnedThemes] = useState<Array<'NEON' | 'CLASSIC' | 'GRID' | 'SUNSET' | 'ICE' | 'VOID' | 'AUTUMN' | 'WINTER' | 'ROYAL'>>(() => stats.unlockedThemeIds as Array<'NEON' | 'CLASSIC' | 'GRID' | 'SUNSET' | 'ICE' | 'VOID' | 'AUTUMN' | 'WINTER' | 'ROYAL'> || ['NEON']);
  const [ownedStyles, setOwnedStyles] = useState<Array<'SOLID' | 'GLOW' | 'OUTLINE'>>(() => stats.unlockedStyleIds as Array<'SOLID' | 'GLOW' | 'OUTLINE'> || ['GLOW']);
  const [ownedMapCards, setOwnedMapCards] = useState<string[]>(() => stats.unlockedMapIds || ['default']);
  const [ownedBoosters, setOwnedBoosters] = useState<Array<'TRAJECTORY' | 'TRAJECTORY_SUB' | 'SOFT_MAGNET' | 'SOFT_SLOW' | 'STABILITY'>>(() => stats.unlockedBoosterIds as Array<'TRAJECTORY' | 'TRAJECTORY_SUB' | 'SOFT_MAGNET' | 'SOFT_SLOW' | 'STABILITY'> || []);
  const [isStoreOpen, setIsStoreOpen] = useState(false);
  const [isTasksOpen, setIsTasksOpen] = useState(false);
  const [isInventoryOpen, setIsInventoryOpen] = useState(false);
  const [isHackerOpen, setIsHackerOpen] = useState(false);
  const [claimedTaskIds, setClaimedTaskIds] = useState<string[]>(() => {
    const saved = localStorage.getItem('neon_pong_claimed_tasks');
    return saved ? JSON.parse(saved) : [];
  });

  useEffect(() => {
    localStorage.setItem('neon_pong_claimed_tasks', JSON.stringify(claimedTaskIds));
  }, [claimedTaskIds]);

  useEffect(() => {
    const dailyKey = getResetKey('daily');
    const weeklyKey = getResetKey('weekly');
    const monthlyKey = getResetKey('monthly');
    setClaimedTaskIds(prev => prev.filter(id => id.endsWith(`_${dailyKey}`) || id.endsWith(`_${weeklyKey}`) || id.endsWith(`_${monthlyKey}`)));
  }, []);

  // Initialize User State
  useEffect(() => {
      const user = AuthService.getCurrentUser();
      if (user) setCurrentUser(user);
  }, []);

  // Global Cheat State
  const [cheatConfig, setCheatConfig] = useState<CheatConfig>({
    paddleSizeMultiplier: 1.0,
    autoPlay: false,
    invisibleOpponent: false,
    slowMotion: false,
    showHelpers: false,
    freezeOpponentUntil: 0,
    jitterAmount: 0,
    rapidFire: false,
    lagSeverity: 0,
    stopWorld: false,
    pendingAction: null,
    ghostHit: false,
    magneticPaddle: false,
    glitchMode: false,
    opponentPaddleMultiplier: 1.0,
    opponentAutoPlay: false,
    trajectoryPreview: false,
    trajectoryBoost: false,
    trajectoryCount: 1,
    stealthAssist: false,
    hideCheatUI: false,
    ultraCheat: false,
    ballControl: false,
    ballControlAngle: 0,
    autoLevelBoost: false,
    serveTarget: 'RANDOM',
    controlThumbScale: 1
  });

  const [isDevPanelOpen, setIsDevPanelOpen] = useState(false);
  const [isCheatDockVisible, setIsCheatDockVisible] = useState(true);
  const [cheatDockPos, setCheatDockPos] = useState({ x: 20, y: 120 });

  useEffect(() => {
    if (!isDevPanelOpen) {
      setIsCheatDockVisible(true);
    }
  }, [isDevPanelOpen]);
  const [devPanelTab, setDevPanelTab] = useState<'ADMIN' | 'DEV'>('ADMIN');
  const [isAchievementsOpen, setIsAchievementsOpen] = useState(false);
  const [showCongrats, setShowCongrats] = useState(false);
  const [showLevelChallenge, setShowLevelChallenge] = useState(false);

  // Sync Data
  useEffect(() => {
    if (currentUser) {
        const unlockedIds = achievements.filter(a => a.isUnlocked).map(a => a.id);
        const updatedUser = {
          ...currentUser,
          achievements: unlockedIds,
          stats: {
            ...stats,
            unlockedThemeIds: ownedThemes,
            unlockedStyleIds: ownedStyles,
            unlockedMapIds: ownedMapCards,
            unlockedBoosterIds: ownedBoosters
          }
        };
        AuthService.updateUser(updatedUser);
    } else {
        localStorage.setItem('neon_pong_achievements', JSON.stringify(achievements));
        localStorage.setItem('neon_pong_stats', JSON.stringify({
          ...stats,
          unlockedThemeIds: ownedThemes,
          unlockedStyleIds: ownedStyles,
          unlockedMapIds: ownedMapCards,
          unlockedBoosterIds: ownedBoosters
        }));
    }

    const allUnlocked = achievements.length > 0 && achievements.every(a => a.isUnlocked);
    if (allUnlocked && !localStorage.getItem('neon_pong_congrats_shown')) {
        setShowCongrats(true);
        localStorage.setItem('neon_pong_congrats_shown', 'true');
    }
  }, [achievements, stats, ownedThemes, ownedStyles, ownedMapCards, ownedBoosters, currentUser?.id]);

  const handleLogin = (user: User) => {
      setCurrentUser(user);
      setAchievements(mergeAchievements(user.achievements));
      setStats(user.stats);
      setOwnedThemes((user.stats.unlockedThemeIds as Array<'NEON' | 'CLASSIC' | 'GRID' | 'SUNSET' | 'ICE' | 'VOID'>) || ['NEON']);
      setOwnedStyles((user.stats.unlockedStyleIds as Array<'SOLID' | 'GLOW' | 'OUTLINE'>) || ['GLOW']);
      setOwnedMapCards(user.stats.unlockedMapIds || ['default']);
      setOwnedBoosters((user.stats.unlockedBoosterIds as Array<'TRAJECTORY' | 'TRAJECTORY_SUB' | 'SOFT_MAGNET' | 'SOFT_SLOW' | 'STABILITY'>) || []);
  };

  const handleLogout = () => {
      AuthService.logout();
      setCurrentUser(null);
      
      const savedAch = localStorage.getItem('neon_pong_achievements');
      const defaults = generateAchievements();
      if (savedAch) {
        const parsed = JSON.parse(savedAch) as Achievement[];
        const merged = defaults.map(def => {
            const found = parsed.find(p => p.id === def.id);
            return found ? { ...def, isUnlocked: found.isUnlocked } : def;
        });
        setAchievements(merged);
      } else {
        setAchievements(defaults);
      }

      const savedStatsRaw = localStorage.getItem('neon_pong_stats');
      const savedStats = savedStatsRaw ? JSON.parse(savedStatsRaw) : { totalWins: 0, totalLosses: 0, totalExits: 0, totalGamesPlayed: 0, totalScore: 0, maxRally: 0, level: 0, coins: 0 };
      setStats(savedStats);
      setOwnedThemes(savedStats.unlockedThemeIds || ['NEON']);
      setOwnedStyles(savedStats.unlockedStyleIds || ['GLOW']);
      setOwnedMapCards(savedStats.unlockedMapIds || ['default']);
      setOwnedBoosters(savedStats.unlockedBoosterIds || []);
  };

  const unlockAchievement = (id: string) => {
    setAchievements(prev => {
      const exists = prev.find(a => a.id === id);
      if (exists && !exists.isUnlocked) {
        return prev.map(a => a.id === id ? { ...a, isUnlocked: true } : a);
      }
      return prev;
    });
  };
  
  const toggleAchievement = (id: string) => {
      setAchievements(prev => prev.map(a => 
        a.id === id ? { ...a, isUnlocked: !a.isUnlocked } : a
      ));
  };

  const updateStats = (newStats: Partial<GameStats> & { didWin?: boolean }) => {
    setStats(prev => {
      const winsDelta = newStats.totalWins ?? 0;
      const gamesDelta = newStats.totalGamesPlayed ?? 0;
      const scoreDelta = newStats.totalScore ?? 0;
      const lossesDelta = newStats.totalLosses ?? 0;
      const exitsDelta = newStats.totalExits ?? 0;

      const nextLevel = Math.min(700, prev.level + (newStats.didWin ? 1 : 0));
      const updated: GameStats = {
        totalWins: prev.totalWins + winsDelta,
        totalLosses: prev.totalLosses + lossesDelta,
        totalExits: prev.totalExits + exitsDelta,
        totalGamesPlayed: prev.totalGamesPlayed + gamesDelta,
        totalScore: prev.totalScore + scoreDelta,
        maxRally: Math.max(prev.maxRally, newStats.maxRally || 0),
        level: nextLevel,
        coins: prev.coins + (newStats.didWin ? 10 : 2)
      };

      if (nextLevel >= 99 && prev.level < 99) {
        setShowLevelChallenge(true);
      }
      if (nextLevel >= 700 && prev.level < 700) {
        setShowCongrats(true);
      }

      checkStatAchievements(updated);
      return updated;
    });
  };

  const checkStatAchievements = (currentStats: GameStats) => {
    const toUnlock: string[] = [];
    
    // Check Wins
    [1, 5, 10, 25, 50, 100, 200, 500, 1000].forEach(target => {
      if (currentStats.totalWins >= target) toUnlock.push(`win_${target}`);
    });

    // Check Score
    [10, 50, 100, 500, 1000, 5000, 10000].forEach(target => {
      if (currentStats.totalScore >= target) toUnlock.push(`score_${target}`);
    });

    // Check Levels
    if (currentStats.level >= 1) toUnlock.push('level_1');
    if (currentStats.level >= 10) toUnlock.push('level_10');
    if (currentStats.level >= 50) toUnlock.push('level_50');
    if (currentStats.level >= 99) toUnlock.push('level_99');
    if (currentStats.level >= 100) toUnlock.push('level_100');
    if (currentStats.level >= 300) toUnlock.push('level_300');

    // Check Generic Play
    for (let i = 1; i <= 20; i++) {
      if (currentStats.totalGamesPlayed >= i * 5) toUnlock.push(`generic_play_${i}`);
    }

    toUnlock.forEach(id => unlockAchievement(id));
  };

  const [opponent, setOpponent] = useState<OpponentType>('BOT');
  const [playerSide, setPlayerSide] = useState<PlayerSide>('RED');
  const [difficulty, setDifficulty] = useState<BotDifficulty>('EASY');
  const [unlockedModes, setUnlockedModes] = useState({ admin: false, dev: false, ultra: false });
  const [trainingCompleted, setTrainingCompleted] = useState(() => localStorage.getItem('neon_pong_training') === 'true');
  const [gameConfig, setGameConfig] = useState<GameConfig>({
    winCondition: 'SCORE',
    winValue: 10,
    paddleSizeMultiplier: 1.0,
    arenaTheme: 'NEON',
  });

  const handleMenuSelect = (
    selectedOpponent: OpponentType, 
    selectedDifficulty?: BotDifficulty,
    config?: GameConfig
  ) => {
    setOpponent(selectedOpponent);
    if (selectedDifficulty) {
      setDifficulty(selectedDifficulty);
    }
    if (config) {
      const activeBoosters = stats.activeBoosters || [];
      const assistConfig = {
        trajectory: activeBoosters.includes('TRAJECTORY') || activeBoosters.includes('TRAJECTORY_SUB'),
        softMagnet: activeBoosters.includes('SOFT_MAGNET'),
        softSlow: activeBoosters.includes('SOFT_SLOW'),
        stability: activeBoosters.includes('STABILITY')
      };
      setGameConfig({
        ...config,
        arenaTheme: stats.activeThemeId ?? config.arenaTheme,
        paddleStyle: stats.activeStyleId ?? config.paddleStyle,
        mapCardId: stats.activeMapCardId ?? 'default',
        assistConfig
      });
    }
    setMode('SELECT_SIDE');
  };

  const handleTrainingComplete = () => {
    setTrainingCompleted(true);
    localStorage.setItem('neon_pong_training', 'true');
  };

  const handleTeamSelect = (side: PlayerSide) => {
    setPlayerSide(side);
    setMode('PLAYING');
  };

  const handleExitGame = () => {
    setMode('MENU');
    setMultiplayerRole('NONE');
    setCheatConfig(prev => ({ ...prev, stopWorld: false, rapidFire: false, autoPlay: false }));
    updateStats({ totalExits: 1 });
  };

  const handleOnlineGameStart = (role: MultiplayerRole, config?: GameConfig) => {
    setMultiplayerRole(role);
    setOpponent('FRIEND'); // Logic behaves like friend (human)
    setPlayerSide(role === 'HOST' ? 'RED' : 'BLUE');
    setDifficulty('EASY'); // Irrelevant
    if (config) {
      setGameConfig(prev => ({
        ...prev,
        winCondition: config.winCondition,
        winValue: config.winValue,
        arenaTheme: config.arenaTheme
      }));
    }
    setMode('PLAYING');
  };
  
  const handleOpenDev = (tab: 'ADMIN' | 'DEV') => {
      setDevPanelTab(tab);
      setIsDevPanelOpen(true);
      setIsCheatDockVisible(false);
  };

  const handleUpdateCheat = (updates: Partial<CheatConfig>) => {
      setCheatConfig(prev => {
        const next = { ...prev, ...updates };
        if (updates.trajectoryPreview !== undefined) {
          setStats(prevStats => {
            const active = prevStats.activeBoosters || [];
            const hasTrajectory = active.includes('TRAJECTORY') || active.includes('TRAJECTORY_SUB');
            return { ...prevStats, activeBoosters: updates.trajectoryPreview ? (hasTrajectory ? active : [...active, 'TRAJECTORY']) : active.filter(id => id !== 'TRAJECTORY') };
          });
        }
        return next;
      });
  };

  const handleSelectTheme = (theme: 'NEON' | 'CLASSIC' | 'GRID' | 'SUNSET' | 'ICE' | 'VOID' | 'AUTUMN' | 'WINTER' | 'ROYAL') => {
    if (!ownedThemes.includes(theme)) return;
    setStats(prev => ({ ...prev, activeThemeId: theme }));
  };

  const handleSelectStyle = (style: 'SOLID' | 'GLOW' | 'OUTLINE') => {
    if (!ownedStyles.includes(style)) return;
    setStats(prev => ({ ...prev, activeStyleId: style }));
  };

  const handleSelectMapCard = (cardId: string) => {
    if (!ownedMapCards.includes(cardId)) return;
    setStats(prev => ({ ...prev, activeMapCardId: cardId }));
  };

  const handleToggleBooster = (boosterId: 'TRAJECTORY' | 'TRAJECTORY_SUB' | 'SOFT_MAGNET' | 'SOFT_SLOW' | 'STABILITY') => {
    if (!ownedBoosters.includes(boosterId)) return;
    setStats(prev => {
      const current = prev.activeBoosters || [];
      const exists = current.includes(boosterId);
      return { ...prev, activeBoosters: exists ? current.filter(id => id !== boosterId) : [...current, boosterId] };
    });
  };

  const handleSetLevel = (level: number) => {
      const clamped = Math.min(700, Math.max(0, level));
      if (clamped >= 700) {
        setShowCongrats(true);
      }
      setStats(prev => ({ ...prev, level: clamped }));
  };

  const handleBuyTheme = (theme: 'NEON' | 'CLASSIC' | 'GRID' | 'SUNSET' | 'ICE' | 'VOID' | 'AUTUMN' | 'WINTER' | 'ROYAL', price: number) => {
      if (stats.coins < price || ownedThemes.includes(theme)) return;
      setStats(prev => ({ ...prev, coins: prev.coins - price, activeThemeId: theme }));
      setOwnedThemes(prev => [...prev, theme]);
      if (ownedThemes.length + 1 >= 9) {
        setShowCongrats(true);
      }
  };

  const handleBuyStyle = (style: 'SOLID' | 'GLOW' | 'OUTLINE', price: number) => {
      if (stats.coins < price || ownedStyles.includes(style)) return;
      setStats(prev => ({ ...prev, coins: prev.coins - price, activeStyleId: style }));
      setOwnedStyles(prev => [...prev, style]);
  };

  const handleBuyMapCard = (cardId: string, price: number) => {
      if (stats.coins < price || ownedMapCards.includes(cardId)) return;
      setStats(prev => ({ ...prev, coins: prev.coins - price, activeMapCardId: cardId }));
      setOwnedMapCards(prev => [...prev, cardId]);
  };

  const handleBuyBooster = (boosterId: 'TRAJECTORY' | 'TRAJECTORY_SUB' | 'SOFT_MAGNET' | 'SOFT_SLOW' | 'STABILITY', price: number) => {
      if (stats.coins < price || ownedBoosters.includes(boosterId)) return;
      setStats(prev => ({ ...prev, coins: prev.coins - price, activeBoosters: [...(prev.activeBoosters || []), boosterId] }));
      setOwnedBoosters(prev => [...prev, boosterId]);
  };

  const handleBuyAll = () => {
      setOwnedThemes(['NEON', 'CLASSIC', 'GRID', 'SUNSET', 'ICE', 'VOID']);
      setOwnedStyles(['SOLID', 'GLOW', 'OUTLINE']);
      setOwnedMapCards(Array.from({ length: 300 }).map((_, i) => `map_${i + 1}`));
      setOwnedBoosters(['TRAJECTORY', 'TRAJECTORY_SUB', 'SOFT_MAGNET', 'SOFT_SLOW', 'STABILITY']);
      setStats(prev => ({
        ...prev,
        activeThemeId: prev.activeThemeId ?? 'NEON',
        activeStyleId: prev.activeStyleId ?? 'GLOW',
        activeMapCardId: prev.activeMapCardId ?? 'default',
        activeBoosters: ['TRAJECTORY', 'TRAJECTORY_SUB', 'SOFT_MAGNET', 'SOFT_SLOW', 'STABILITY']
      }));
  };


  const handleClaimTask = (taskId: string, reward: number) => {
      if (claimedTaskIds.includes(taskId)) return;
      setClaimedTaskIds(prev => [...prev, taskId]);
      setStats(prev => ({ ...prev, coins: prev.coins + reward }));
  };

  const handleOpenStore = () => {
    if (!currentUser) {
      setIsAuthModalOpen(true);
      return;
    }
    setIsStoreOpen(true);
  };

  const handleOpenTasks = () => {
    if (!currentUser) {
      setIsAuthModalOpen(true);
      return;
    }
    setIsTasksOpen(true);
  };

  const handleOpenInventory = () => {
    if (!currentUser) {
      setIsAuthModalOpen(true);
      return;
    }
    setIsInventoryOpen(true);
  };

  return (
    <div className="h-[100dvh] w-full bg-slate-950 flex flex-col items-center justify-center overflow-hidden font-sans">
      
      {/* Background Decor */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute top-0 left-0 w-full h-full bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-slate-900 via-slate-950 to-black opacity-80"></div>
        <div className="absolute top-1/4 left-1/4 w-[500px] h-[500px] bg-blue-500/5 rounded-full blur-[100px] animate-pulse"></div>
        <div className="absolute bottom-1/4 right-1/4 w-[500px] h-[500px] bg-red-500/5 rounded-full blur-[100px] animate-pulse delay-700"></div>
        <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20"></div>
      </div>
      <div className="relative z-10 w-full h-full flex flex-col justify-center">
        {mode === 'MENU' && (
          <MainMenu 
            onSelect={handleMenuSelect}
            onOpenTraining={() => setMode('TRAINING')}
            trainingCompleted={trainingCompleted} 
            onUnlockMode={(mode) => {
              setUnlockedModes(prev => ({ ...prev, [mode]: true }));
              if (mode === 'admin') unlockAchievement('admin_mode');
              if (mode === 'dev') unlockAchievement('dev_mode');
            }}
            unlockedModes={unlockedModes}
            onOpenAchievements={() => setIsAchievementsOpen(true)}
            currentUser={currentUser}
            onLoginClick={() => setIsAuthModalOpen(true)}
            onLogout={handleLogout}
            language={language}
            setLanguage={setLanguage}
            onOnlineClick={() => setMode('ONLINE_LOBBY')}
            onSpectate={() => {
                setOpponent('BOT');
                setDifficulty('IMPOSSIBLE');
                setGameConfig(prev => ({ ...prev, paddleSizeMultiplier: 1.0 }));
                setCheatConfig(prev => ({ ...prev, autoPlay: true }));
                setMode('PLAYING');
            }}
            isCheatHidden={cheatConfig.hideCheatUI}
            onToggleCheatHidden={() => setCheatConfig(prev => ({ ...prev, hideCheatUI: !prev.hideCheatUI }))}
            onSetLevel={handleSetLevel}
            playerLevel={stats.level}
            onOpenStore={handleOpenStore}
            onOpenTasks={handleOpenTasks}
            onOpenInventory={handleOpenInventory}
          />
        )}
        
        {mode === 'ONLINE_LOBBY' && (
            <OnlineLobby 
                language={language}
                user={currentUser}
                onBack={() => setMode('MENU')}
                onRegisterClick={() => {
                    setMode('MENU');
                    setTimeout(() => setIsAuthModalOpen(true), 100);
                }}
                onGameStart={handleOnlineGameStart}
            />
        )}

        {mode === 'SELECT_SIDE' && (
          <TeamSelect 
            opponent={opponent} 
            onSelect={handleTeamSelect} 
            onBack={() => setMode('MENU')} 
          />
        )}

        {mode === 'PLAYING' && (
          <PongGame 
            opponent={opponent} 
            playerSide={playerSide} 
            difficulty={difficulty}
            gameConfig={gameConfig}
            unlockedModes={unlockedModes}
            onExit={handleExitGame}
            onUpdateStats={updateStats}
            cheatConfig={cheatConfig}
            onUpdateCheatConfig={handleUpdateCheat}
            onOpenDevPanel={() => handleOpenDev(unlockedModes.dev ? 'DEV' : 'ADMIN')}
            multiplayerRole={multiplayerRole}
          />
        )}

        {mode === 'TRAINING' && (
          <TrainingScreen
            onBack={() => setMode('MENU')}
            onComplete={() => {
              handleTrainingComplete();
              setOpponent('BOT');
              setDifficulty('EASY');
              setPlayerSide('RED');
              setGameConfig({
                winCondition: 'SCORE',
                winValue: 3,
                paddleSizeMultiplier: 1.1,
                arenaTheme: 'NEON'
              });
              setMode('PLAYING');
            }}
            canSkip={unlockedModes.ultra}
            onSkip={() => {
              handleTrainingComplete();
              setMode('MENU');
            }}
          />
        )}

      {(unlockedModes.admin || unlockedModes.dev) && isCheatDockVisible && (
        <CheatDock
          visible={isCheatDockVisible}
          onOpen={() => setIsDevPanelOpen(true)}
          position={cheatDockPos}
          onPositionChange={setCheatDockPos}
        />
      )}
      </div>
      
      {/* Global Overlays */}
      <DevPanel 
         isOpen={isDevPanelOpen}
         onClose={() => setIsDevPanelOpen(false)}
         onMinimize={() => {
           setIsDevPanelOpen(false);
           setIsCheatDockVisible(true);
         }}
         config={cheatConfig}
         onUpdate={handleUpdateCheat}
         unlockedModes={unlockedModes}
         onOpenHacker={() => setIsHackerOpen(true)}
         onAddCoins={(amount) => setStats(prev => ({ ...prev, coins: prev.coins + amount }))}
         onSetCoins={(amount) => setStats(prev => ({ ...prev, coins: amount }))}
         initialTab={devPanelTab}
         language={language}
      />

      {isAchievementsOpen && (
          <AchievementsMenu 
             achievements={achievements}
             onClose={() => setIsAchievementsOpen(false)}
             stats={stats}
             onUnlockAll={unlockedModes.dev ? () => setAchievements(prev => prev.map(a => ({ ...a, isUnlocked: true }))) : undefined}
             onToggle={unlockedModes.dev ? toggleAchievement : undefined}
          />
      )}
      
      {showCongrats && (
          <CongratsModal onClose={() => setShowCongrats(false)} />
      )}

      {showLevelChallenge && (
        <LevelChallengeModal
          onTakeSafeLevel={() => {
            setStats(prev => ({ ...prev, level: Math.max(prev.level, 100) }));
            setShowLevelChallenge(false);
          }}
          onAcceptChallenge={() => {
            setShowLevelChallenge(false);
          }}
          onClose={() => setShowLevelChallenge(false)}
        />
      )}

      <StorePanel
        isOpen={isStoreOpen}
        onClose={() => setIsStoreOpen(false)}
        coins={stats.coins}
        ownedThemes={ownedThemes}
        ownedStyles={ownedStyles}
        ownedMapCards={ownedMapCards}
        ownedBoosters={ownedBoosters}
        onBuyTheme={handleBuyTheme}
        onBuyStyle={handleBuyStyle}
        onBuyMapCard={handleBuyMapCard}
        onBuyBooster={handleBuyBooster}
      />

      <InventoryPanel
        isOpen={isInventoryOpen}
        onClose={() => setIsInventoryOpen(false)}
        ownedThemes={ownedThemes}
        ownedStyles={ownedStyles}
        ownedMapCards={ownedMapCards}
        ownedBoosters={ownedBoosters}
        activeThemeId={stats.activeThemeId}
        activeStyleId={stats.activeStyleId}
        activeMapCardId={stats.activeMapCardId}
        activeBoosters={stats.activeBoosters || []}
        onSelectTheme={handleSelectTheme}
        onSelectStyle={handleSelectStyle}
        onSelectMapCard={handleSelectMapCard}
        onToggleBooster={handleToggleBooster}
      />

      <HackerPanel
        isOpen={isHackerOpen}
        onClose={() => setIsHackerOpen(false)}
        config={cheatConfig}
        onUpdate={handleUpdateCheat}
        onAddCoins={(amount) => setStats(prev => ({ ...prev, coins: prev.coins + amount }))}
        onSetCoins={(amount) => setStats(prev => ({ ...prev, coins: amount }))}
        onBuyAll={handleBuyAll}
      />

      <TasksPanel
        isOpen={isTasksOpen}
        onClose={() => setIsTasksOpen(false)}
        language={language}
        coins={stats.coins}
        stats={{ totalWins: stats.totalWins, totalScore: stats.totalScore, totalGamesPlayed: stats.totalGamesPlayed }}
        claimedTaskIds={claimedTaskIds}
        onClaim={handleClaimTask}
      />

      <AuthModal 
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        onLogin={handleLogin}
      />
    </div>
  );
}
