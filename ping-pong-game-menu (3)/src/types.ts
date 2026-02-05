export type Language = 'ru' | 'en';

export type GameMode = 'MENU' | 'SELECT_SIDE' | 'PLAYING' | 'GAME_OVER';
export type OpponentType = 'BOT' | 'FRIEND';
export type PlayerSide = 'RED' | 'BLUE';
export type BotDifficulty = 'EASY' | 'NORMAL' | 'ADAPTIVE' | 'HARD' | 'EXPERT' | 'MASTER' | 'NIGHTMARE' | 'IMPOSSIBLE';
export type WinCondition = 'SCORE' | 'TIME';
export type ArenaTheme = 'CLASSIC' | 'NEON' | 'GRID' | 'SUNSET' | 'ICE' | 'VOID' | 'AUTUMN' | 'WINTER' | 'ROYAL';
export type PaddleStyle = 'SOLID' | 'GLOW' | 'OUTLINE';
export type BoosterId = 'TRAJECTORY' | 'TRAJECTORY_SUB' | 'SOFT_MAGNET' | 'SOFT_SLOW' | 'STABILITY';
export type BallSkinId = 'NEON' | 'ICE' | 'RUBY' | 'GOLD' | 'VOID';

export interface AssistConfig {
  trajectory: boolean;
  softMagnet: boolean;
  softSlow: boolean;
  stability: boolean;
}

export interface GameConfig {
  winCondition: WinCondition;
  winValue: number; // Score (e.g. 10) or Time in seconds (e.g. 60)
  paddleSizeMultiplier: number; // 1.0 to 1.5
  arenaTheme: ArenaTheme;
  paddleStyle?: PaddleStyle;
  mapCardId?: string;
  ballSkinId?: BallSkinId;
  assistConfig?: AssistConfig;
}

export interface GameState {
  mode: GameMode;
  opponent: OpponentType;
  playerSide: PlayerSide;
  difficulty: BotDifficulty;
  score: { red: number; blue: number };
  winner: PlayerSide | null;
}

export type CheatAction = 
  | { type: 'ADD_SCORE', who: 'me' | 'enemy', amount: number }
  | { type: 'FORCE_WIN' }
  | { type: 'RESET_GAME' };

export interface CheatConfig {
  paddleSizeMultiplier: number; // Normal is 1.0. Admin can go to 3.0. Dev can go to 10.0
  autoPlay: boolean; // "God Mode"
  invisibleOpponent: boolean;
  slowMotion: boolean;
  showHelpers: boolean; // Trajectory helper
  freezeOpponentUntil: number; // Timestamp when freeze ends
  jitterAmount: number; // 0 to 100 - randomness added to opponent movement
  rapidFire: boolean; // Teleport ball to opponent goal repeatedly
  lagSeverity: number; // 0-100% chance to skip frame for opponent
  stopWorld: boolean; // Completely pause game state
  pendingAction: CheatAction | null; // Command to execute in game loop
  ghostHit: boolean; // "Ghost Hit" - Bounce ball if missed but close
  magneticPaddle: boolean; // "Magnetic Paddle" - Paddle pulls itself to ball
  glitchMode: boolean; // "Glitch Mode" - Enemy lags, ball acts psycho, auto-hit
  opponentPaddleMultiplier: number; // Bot paddle size boost
  opponentAutoPlay: boolean; // Bot god mode
  trajectoryPreview: boolean; // Show predicted trajectory for player
  trajectoryBoost: boolean; // Extra long trajectory preview
  trajectoryCount: number; // Trajectory segments (bounces) to show
  stealthAssist: boolean; // Subtle assist to win without being noticed
  hideCheatUI: boolean; // Hide cheat indicators in-game
  ultraCheat: boolean; // Triple-pin super cheat
  ballControl: boolean; // Manual trajectory control
  ballControlAngle: number; // -60..60 degrees
  autoLevelBoost: boolean; // Auto level increase while online
  serveTarget: 'PLAYER' | 'OPPONENT' | 'RANDOM'; // Who receives the first serve
  controlThumbScale?: number; // UI control thumb scale
}

export interface Achievement {
  id: string;
  title: string;
  description: string;
  icon: string;
  isUnlocked: boolean;
  category: 'bronze' | 'silver' | 'gold' | 'platinum' | 'secret';
}

export interface GameStats {
  totalWins: number;
  totalLosses: number;
  totalExits: number;
  totalGamesPlayed: number;
  totalScore: number;
  maxRally: number;
  level: number;
  coins: number;
  unlockedThemeIds?: string[];
  unlockedStyleIds?: string[];
  unlockedMapIds?: string[];
  unlockedBoosterIds?: BoosterId[];
  unlockedBallSkinIds?: BallSkinId[];
  activeThemeId?: ArenaTheme;
  activeStyleId?: PaddleStyle;
  activeMapCardId?: string;
  activeBoosters?: BoosterId[];
  activeBallSkinId?: BallSkinId;
}

export interface StatsUpdate {
  totalWins?: number;
  totalLosses?: number;
  totalExits?: number;
  totalGamesPlayed?: number;
  totalScore?: number;
  maxRally?: number;
  levelDelta?: number;
  didWin?: boolean;
}

export interface User {
  id: string;
  username: string;
  email: string;
  passwordHash: string;
  achievements: string[]; // List of unlocked achievement IDs
  stats: GameStats;
}

export interface OnlineRoom {
  id: string;
  hostName: string;
  name: string;
  isLocked: boolean;
  players: number;
}

export type MultiplayerRole = 'HOST' | 'CLIENT' | 'NONE';

export interface MultiplayerData {
  type: 'SYNC' | 'PADDLE_MOVE' | 'SCORE_UPDATE' | 'GAME_OVER' | 'AUTH' | 'AUTH_OK' | 'AUTH_FAIL' | 'CONFIG';
  timestamp: number;
  payload: any;
}

