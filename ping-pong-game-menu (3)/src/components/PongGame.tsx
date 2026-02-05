import React, { useRef, useEffect, useState, useCallback } from 'react';
import { GameConfig, CheatConfig, PlayerSide, OpponentType, BotDifficulty, MultiplayerRole, GameStats, ArenaTheme } from '../types';
import { GameControls } from './GameControls';
import { SettingsModal } from './SettingsModal';
import { Settings, Maximize2, Minimize2, Pause, Play, Home, Volume2, VolumeX } from 'lucide-react';
import { soundManager } from '../utils/sound';
import { socketService } from '../services/socket';

interface PongGameProps {
  opponent: OpponentType;
  playerSide: PlayerSide;
  difficulty: BotDifficulty;
  gameConfig: GameConfig;
  unlockedModes: { admin: boolean; dev: boolean };
  onExit: () => void;
  onUpdateStats: (stats: Partial<GameStats> & { didWin?: boolean }) => void;
  cheatConfig: CheatConfig;
  onUpdateCheatConfig: (config: Partial<CheatConfig>) => void;
  onOpenDevPanel: () => void;
  multiplayerRole: MultiplayerRole;
}

export const PongGame: React.FC<PongGameProps> = ({
  opponent,
  playerSide,
  difficulty,
  gameConfig,
  onExit,
  onUpdateStats,
  cheatConfig,
  onUpdateCheatConfig,
  multiplayerRole
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const animationRef = useRef<number | null>(null);
  const soundRef = useRef(soundManager);
  
  // КРИТИЧНО: Всегда актуальная ссылка на читы
  const cheatRef = useRef(cheatConfig);
  cheatRef.current = cheatConfig;
  
  // Состояние игры
  const [showSettings, setShowSettings] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [scores, setScores] = useState({ player1: 0, player2: 0 });
  const [gameOver, setGameOver] = useState(false);
  const [winner, setWinner] = useState<string | null>(null);
  const [ballSize, setBallSize] = useState(1);
  const [arenaTheme, setArenaTheme] = useState<ArenaTheme>(gameConfig.arenaTheme);
  const isOnline = multiplayerRole !== 'NONE';
  const onlineRole = multiplayerRole;
  const onlineRef = useRef({ isOnline, role: onlineRole });
  onlineRef.current = { isOnline, role: onlineRole };
  
  // Размеры
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  
  // Рефы для игрового цикла
  const gameStateRef = useRef({
    ballX: 0.5,
    ballY: 0.5,
    ballVX: 0.008,
    ballVY: 0.005,
    serveReady: true,
    player1Y: 0.5,
    player2Y: 0.5,
    score1: 0,
    score2: 0
  });

  const lastProcessedActionRef = useRef<number>(0);
  
  const inputRef = useRef({ player1: 50, player2: 50 });
  const isMutedRef = useRef(isMuted);
  isMutedRef.current = isMuted;

  // Инициализация звука и онлайн синхронизация
  useEffect(() => {
    soundRef.current = soundManager;
  }, []);

  useEffect(() => {
    if (multiplayerRole === 'NONE') return;
    socketService.onGameUpdate((data) => {
      if (!data) return;
      if (multiplayerRole === 'CLIENT') {
        const state = gameStateRef.current;
        state.ballX = data.ballX ?? state.ballX;
        state.ballY = data.ballY ?? state.ballY;
        state.ballVX = data.ballVX ?? state.ballVX;
        state.ballVY = data.ballVY ?? state.ballVY;
        state.player1Y = data.player1Y ?? state.player1Y;
        state.player2Y = data.player2Y ?? state.player2Y;
        state.score1 = data.score1 ?? state.score1;
        state.score2 = data.score2 ?? state.score2;
        setScores({ player1: state.score1, player2: state.score2 });
      }
    });
  }, [multiplayerRole]);

  // Обновление размеров
  useEffect(() => {
    const updateSize = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        setDimensions({ 
          width: Math.floor(rect.width), 
          height: Math.floor(rect.height - 120)
        });
      }
    };
    updateSize();
    window.addEventListener('resize', updateSize);
    return () => window.removeEventListener('resize', updateSize);
  }, []);

  // Предсказание траектории мяча для Режима Бога
  const predictBallY = useCallback((ballX: number, ballY: number, ballVX: number, ballVY: number, targetX: number): number => {
    let x = ballX;
    let y = ballY;
    let vx = ballVX;
    let vy = ballVY;
    
    if ((targetX < 0.5 && vx > 0) || (targetX > 0.5 && vx < 0)) {
      return y;
    }
    
    for (let i = 0; i < 1000; i++) {
      x += vx;
      y += vy;
      
      if (y <= 0 || y >= 1) {
        vy = -vy;
        y = Math.max(0.01, Math.min(0.99, y));
      }
      
      if ((targetX < 0.5 && x <= targetX) || (targetX > 0.5 && x >= targetX)) {
        return Math.max(0, Math.min(1, y));
      }
    }
    
    return y;
  }, []);

  // Основной игровой цикл
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const PADDLE_WIDTH = 0.015;
    const BALL_SIZE_BASE = 0.02;
    const BASE_PADDLE_HEIGHT = 0.15;
    const TARGET_SCORE = gameConfig.winValue || 10;

    const gameLoop = () => {
      // === UPDATE ===
      if (!isPaused && !gameOver) {
        const state = gameStateRef.current;
        const cheats = cheatRef.current;
        const isPlayerRed = playerSide === 'RED';
        
        // ===== РАЗМЕР РАКЕТКИ =====
        const playerPaddleHeight = BASE_PADDLE_HEIGHT * cheats.paddleSizeMultiplier;
        const opponentPaddleHeight = BASE_PADDLE_HEIGHT * (cheats.opponentPaddleMultiplier || 1);
        
        // ===== ОБРАБОТКА ВВОДА =====
        const myY = inputRef.current.player1 / 100;
        const oppY = inputRef.current.player2 / 100;
        
        // ===== РЕЖИМ БОГА (ТОЛЬКО ДЛЯ ИГРОКА) =====
        if (cheats.autoPlay) {
          const targetX = isPlayerRed ? 0.02 : 0.98;
          const predictedY = predictBallY(state.ballX, state.ballY, state.ballVX, state.ballVY, targetX);

          if (isPlayerRed) {
            state.player1Y = predictedY;
          } else {
            state.player2Y = predictedY;
          }
        } else if (cheats.opponentAutoPlay) {
          // BOT-BOX: сверх-помощник игроку, без палева
          const targetX = isPlayerRed ? 0.02 : 0.98;
          const predictedY = predictBallY(state.ballX, state.ballY, state.ballVX, state.ballVY, targetX);
          const assistStrength = 0.6;
          if (isPlayerRed) {
            state.player1Y += (predictedY - state.player1Y) * assistStrength;
          } else {
            state.player2Y += (predictedY - state.player2Y) * assistStrength;
          }
        } else if (cheats.magneticPaddle) {
          // Магнитная ракетка
          if (isPlayerRed) {
            state.player1Y += (state.ballY - state.player1Y) * 0.3;
          } else {
            state.player2Y += (state.ballY - state.player2Y) * 0.3;
          }
        } else {
          // Обычное управление
          if (isPlayerRed) {
            state.player1Y = myY;
          } else {
            state.player2Y = myY;
          }
        }
        
        // ===== БОТ ИЛИ ВТОРОЙ ИГРОК =====
        if (opponent === 'BOT') {
          if (cheats.opponentAutoPlay) {
            const targetX = isPlayerRed ? 0.98 : 0.02;
            const predictedY = predictBallY(state.ballX, state.ballY, state.ballVX, state.ballVY, targetX);
            if (isPlayerRed) {
              state.player2Y = predictedY;
            } else {
              state.player1Y = predictedY;
            }
          } else {
            let botSpeed = 0.02;
            let botError = 0.1;
            
            if (difficulty === 'EASY') {
              botSpeed = 0.01;
              botError = 0.3;
            } else if (difficulty === 'IMPOSSIBLE') {
              botSpeed = 1.0;
              botError = 0;
            }
            
            // ЛАГ для бота
            if (cheats.lagSeverity > 0 && Math.random() * 100 < cheats.lagSeverity) {
              // Бот пропускает кадр
            } else {
              const botTarget = state.ballY + (Math.random() - 0.5) * botError;
              if (isPlayerRed) {
                state.player2Y += (botTarget - state.player2Y) * botSpeed;
              } else {
                state.player1Y += (botTarget - state.player1Y) * botSpeed;
              }
            }
          }
        } else if (opponent === 'FRIEND') {
          if (isPlayerRed) {
            state.player2Y = oppY;
          } else {
            state.player1Y = oppY;
          }
        }
        
        // ===== ГЛИТЧ РЕЖИМ =====
        if (cheats.glitchMode) {
          if ((isPlayerRed && state.ballVX > 0) || (!isPlayerRed && state.ballVX < 0)) {
            state.ballVX *= 1.002;
          }
          
          if (Math.random() < 0.1) {
            if (isPlayerRed) {
              state.player2Y += (Math.random() - 0.5) * 0.05;
            } else {
              state.player1Y += (Math.random() - 0.5) * 0.05;
            }
          }
        }

        // ===== УЛЬТРА-ЧИТ (только для игрока) =====
        if (cheats.ultraCheat) {
          const targetX = isPlayerRed ? 0.02 : 0.98;
          const predictedY = predictBallY(state.ballX, state.ballY, state.ballVX, state.ballVY, targetX);
          if (isPlayerRed) {
            state.player1Y = predictedY;
          } else {
            state.player2Y = predictedY;
          }
          const sabotageChance = 0.08;
          if (Math.random() < sabotageChance) {
            state.ballVY += (Math.random() - 0.5) * 0.003;
          }
        }

        if (cheats.ballControl) {
          const angle = (cheats.ballControlAngle * Math.PI) / 180;
          const speed = Math.hypot(state.ballVX, state.ballVY);
          state.ballVX = Math.cos(angle) * speed * (state.ballVX >= 0 ? 1 : -1);
          state.ballVY = Math.sin(angle) * speed;
        }

        // ===== НЕЗАМЕТНЫЙ ПОМОЩНИК (STEALTH ASSIST) =====
        if (cheats.stealthAssist) {
          const isBallThreatening = isPlayerRed ? state.ballVX < 0 : state.ballVX > 0;
          const playerY = isPlayerRed ? state.player1Y : state.player2Y;

          if (isBallThreatening) {
            const assistStrength = 0.05;
            if (isPlayerRed) {
              state.player1Y += (state.ballY - state.player1Y) * assistStrength;
            } else {
              state.player2Y += (state.ballY - state.player2Y) * assistStrength;
            }

            const nearMyPaddle = Math.abs(playerY - state.ballY) < 0.06;
            if (nearMyPaddle) {
              state.ballVX *= 0.995;
            }
          }

          const edgeCatch = Math.abs(playerY - state.ballY) < 0.08;
          if (edgeCatch) {
            state.ballVY += (playerY - state.ballY) * 0.0005;
          }
        }
        
        // ===== RAPID FIRE =====
        if (cheats.rapidFire) {
          if (isPlayerRed) {
            state.score1 += 1;
            setScores(s => ({ ...s, player1: state.score1 }));
          } else {
            state.score2 += 1;
            setScores(s => ({ ...s, player2: state.score2 }));
          }
          
          if (state.score1 >= TARGET_SCORE || state.score2 >= TARGET_SCORE) {
            setGameOver(true);
            setWinner(state.score1 > state.score2 ? 'player1' : 'player2');
          }
        }

        // ===== ЧИТ-КОМАНДЫ (ПЛЮС 99, СБРОС, ПОБЕДА) =====
        if (cheats.pendingAction && cheats.pendingAction.type) {
          const actionTime = Date.now();
          if (actionTime - lastProcessedActionRef.current > 200) {
            if (cheats.pendingAction.type === 'ADD_SCORE') {
              const amount = Number(cheats.pendingAction.amount || 0);
              if (cheats.pendingAction.who === 'me') {
                if (isPlayerRed) {
                  state.score1 += amount;
                  setScores(s => ({ ...s, player1: state.score1 }));
                } else {
                  state.score2 += amount;
                  setScores(s => ({ ...s, player2: state.score2 }));
                }
              } else {
                if (isPlayerRed) {
                  state.score2 += amount;
                  setScores(s => ({ ...s, player2: state.score2 }));
                } else {
                  state.score1 += amount;
                  setScores(s => ({ ...s, player1: state.score1 }));
                }
              }
              lastProcessedActionRef.current = actionTime;
              onUpdateCheatConfig({ pendingAction: null });
            }
            if (cheats.pendingAction.type === 'FORCE_WIN') {
              if (isPlayerRed) {
                state.score1 = TARGET_SCORE;
                setScores(s => ({ ...s, player1: state.score1 }));
              } else {
                state.score2 = TARGET_SCORE;
                setScores(s => ({ ...s, player2: state.score2 }));
              }
              setGameOver(true);
              setWinner(isPlayerRed ? 'player1' : 'player2');
              lastProcessedActionRef.current = actionTime;
              onUpdateCheatConfig({ pendingAction: null });
            }
            if (cheats.pendingAction.type === 'RESET_GAME') {
              state.score1 = 0;
              state.score2 = 0;
              setScores({ player1: 0, player2: 0 });
              setGameOver(false);
              setWinner(null);
              lastProcessedActionRef.current = actionTime;
              onUpdateCheatConfig({ pendingAction: null });
            }
          }
        }
        
        // ===== ЗАМЕДЛЕНИЕ ВРЕМЕНИ =====
        let speedMultiplier = 1;
        if (cheats.slowMotion) speedMultiplier = 0.3;
        if (cheats.stopWorld) speedMultiplier = 0;
        
        // ===== ПОДАЧА =====
        if (state.serveReady) {
          const target = cheats.serveTarget || 'RANDOM';
          const shouldServeToPlayer = target === 'PLAYER' ? true : target === 'OPPONENT' ? false : Math.random() > 0.5;
          const isPlayerRedSide = playerSide === 'RED';
          const serveToLeft = shouldServeToPlayer ? isPlayerRedSide : !isPlayerRedSide;

          state.ballVX = serveToLeft ? -0.008 : 0.008;
          state.ballVY = (Math.random() - 0.5) * 0.01;
          state.serveReady = false;
        }

        // ===== ДВИЖЕНИЕ МЯЧА =====
        state.ballX += state.ballVX * speedMultiplier;
        state.ballY += state.ballVY * speedMultiplier;
        
        if (state.ballY <= BALL_SIZE_BASE / 2 || state.ballY >= 1 - BALL_SIZE_BASE / 2) {
          state.ballVY = -state.ballVY;
          state.ballY = Math.max(BALL_SIZE_BASE / 2, Math.min(1 - BALL_SIZE_BASE / 2, state.ballY));
          if (!isMutedRef.current && soundRef.current) soundRef.current.playWall();
        }
        
        // ===== КОЛЛИЗИЯ С РАКЕТКАМИ =====
        const p1H = isPlayerRed ? playerPaddleHeight : opponentPaddleHeight;
        const p2H = !isPlayerRed ? playerPaddleHeight : opponentPaddleHeight;
        
        const p1Top = state.player1Y - p1H / 2;
        const p1Bottom = state.player1Y + p1H / 2;
        const p2Top = state.player2Y - p2H / 2;
        const p2Bottom = state.player2Y + p2H / 2;
        
        // Левая ракетка
        if (state.ballX <= PADDLE_WIDTH + BALL_SIZE_BASE / 2 && state.ballVX < 0) {
          const hitboxExt = cheats.ghostHit && isPlayerRed ? 0.05 : 0;
          
          if (state.ballY >= p1Top - hitboxExt && state.ballY <= p1Bottom + hitboxExt) {
            state.ballVX = Math.abs(state.ballVX) * 1.02;
            state.ballX = PADDLE_WIDTH + BALL_SIZE_BASE / 2 + 0.01;
            if (!isMutedRef.current && soundRef.current) soundRef.current.playHit();
          }
        }
        
        // Правая ракетка
        if (state.ballX >= 1 - PADDLE_WIDTH - BALL_SIZE_BASE / 2 && state.ballVX > 0) {
          const hitboxExt = cheats.ghostHit && !isPlayerRed ? 0.05 : 0;
          
          if (state.ballY >= p2Top - hitboxExt && state.ballY <= p2Bottom + hitboxExt) {
            state.ballVX = -Math.abs(state.ballVX) * 1.02;
            state.ballX = 1 - PADDLE_WIDTH - BALL_SIZE_BASE / 2 - 0.01;
            if (!isMutedRef.current && soundRef.current) soundRef.current.playHit();
          }
        }
        
        // ===== ГОЛ =====
        if (state.ballX < 0) {
          state.score2 += 1;
          setScores(s => ({ ...s, player2: state.score2 }));
          if (!isMutedRef.current && soundRef.current) soundRef.current.playScore();
          // Reset
          state.ballX = 0.5;
          state.ballY = 0.5;
          state.ballVX = 0.008;
          state.ballVY = (Math.random() - 0.5) * 0.01;
          state.serveReady = true;
        } else if (state.ballX > 1) {
          state.score1 += 1;
          setScores(s => ({ ...s, player1: state.score1 }));
          if (!isMutedRef.current && soundRef.current) soundRef.current.playScore();
          // Reset
          state.ballX = 0.5;
          state.ballY = 0.5;
          state.ballVX = -0.008;
          state.ballVY = (Math.random() - 0.5) * 0.01;
          state.serveReady = true;
        }
        
        // ===== ПРОВЕРКА ПОБЕДЫ =====
        if (state.score1 >= TARGET_SCORE || state.score2 >= TARGET_SCORE) {
          setGameOver(true);
          setWinner(state.score1 > state.score2 ? 'player1' : 'player2');
          const didWin = (state.score1 > state.score2 && playerSide === 'RED') ||
                         (state.score2 > state.score1 && playerSide === 'BLUE');
          onUpdateStats({ 
            totalGamesPlayed: 1, 
            totalWins: didWin ? 1 : 0,
            totalLosses: didWin ? 0 : 1,
            totalScore: playerSide === 'RED' ? state.score1 : state.score2,
            didWin
          });
        }
        
        // Ограничение позиций
        state.player1Y = Math.max(p1H / 2, Math.min(1 - p1H / 2, state.player1Y));
        state.player2Y = Math.max(p2H / 2, Math.min(1 - p2H / 2, state.player2Y));

        // Онлайн синхронизация (ХОСТ отправляет состояние)
        if (onlineRef.current.isOnline && onlineRef.current.role === 'HOST') {
          socketService.sendGameUpdate({
            ballX: state.ballX,
            ballY: state.ballY,
            ballVX: state.ballVX,
            ballVY: state.ballVY,
            player1Y: state.player1Y,
            player2Y: state.player2Y,
            score1: state.score1,
            score2: state.score2
          });
        }
      }

      // === DRAW ===
      const { width, height } = dimensions;
      const state = gameStateRef.current;
      const cheats = cheatRef.current;
      const isPlayerRed = playerSide === 'RED';
      
      canvas.width = width;
      canvas.height = height;
      
      // Фон
      if (arenaTheme === 'CLASSIC') {
        ctx.fillStyle = '#0a0a0a';
        ctx.fillRect(0, 0, width, height);
      } else if (arenaTheme === 'GRID') {
        ctx.fillStyle = '#0b1220';
        ctx.fillRect(0, 0, width, height);
        ctx.strokeStyle = '#1f2937';
        ctx.lineWidth = 1;
        for (let x = 0; x < width; x += 40) {
          ctx.beginPath();
          ctx.moveTo(x, 0);
          ctx.lineTo(x, height);
          ctx.stroke();
        }
        for (let y = 0; y < height; y += 40) {
          ctx.beginPath();
          ctx.moveTo(0, y);
          ctx.lineTo(width, y);
          ctx.stroke();
        }
      } else if (arenaTheme === 'SUNSET') {
        const gradient = ctx.createLinearGradient(0, 0, 0, height);
        gradient.addColorStop(0, '#ff7e5f');
        gradient.addColorStop(1, '#2b1055');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, width, height);
      } else if (arenaTheme === 'ICE') {
        const gradient = ctx.createLinearGradient(0, 0, width, height);
        gradient.addColorStop(0, '#0ea5e9');
        gradient.addColorStop(1, '#0f172a');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, width, height);
      } else if (arenaTheme === 'VOID') {
        ctx.fillStyle = '#05020a';
        ctx.fillRect(0, 0, width, height);
      } else if (arenaTheme === 'AUTUMN') {
        const gradient = ctx.createLinearGradient(0, 0, width, height);
        gradient.addColorStop(0, '#7c2d12');
        gradient.addColorStop(1, '#f59e0b');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, width, height);
        ctx.fillStyle = 'rgba(255,255,255,0.05)';
        for (let i = 0; i < 30; i++) {
          ctx.beginPath();
          ctx.arc(Math.random() * width, Math.random() * height, 3, 0, Math.PI * 2);
          ctx.fill();
        }
      } else if (arenaTheme === 'WINTER') {
        const gradient = ctx.createLinearGradient(0, 0, 0, height);
        gradient.addColorStop(0, '#e0f2fe');
        gradient.addColorStop(1, '#0f172a');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, width, height);
        ctx.fillStyle = 'rgba(255,255,255,0.15)';
        for (let i = 0; i < 60; i++) {
          ctx.beginPath();
          ctx.arc(Math.random() * width, Math.random() * height, 1.5, 0, Math.PI * 2);
          ctx.fill();
        }
      } else if (arenaTheme === 'ROYAL') {
        const gradient = ctx.createLinearGradient(0, 0, width, height);
        gradient.addColorStop(0, '#312e81');
        gradient.addColorStop(1, '#9333ea');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, width, height);
        ctx.strokeStyle = 'rgba(255,255,255,0.08)';
        ctx.lineWidth = 2;
        for (let i = 0; i < 8; i++) {
          ctx.strokeRect(20 + i * 20, 20 + i * 20, width - 40 - i * 40, height - 40 - i * 40);
        }
      } else {
        ctx.fillStyle = '#0f172a';
        ctx.fillRect(0, 0, width, height);
      }
      
      // Сетка
      ctx.strokeStyle = '#1e293b';
      ctx.lineWidth = 2;
      ctx.setLineDash([10, 10]);
      ctx.beginPath();
      ctx.moveTo(width / 2, 0);
      ctx.lineTo(width / 2, height);
      ctx.stroke();
      ctx.setLineDash([]);
      
      // Размеры ракеток
      const playerPaddleH = height * BASE_PADDLE_HEIGHT * cheats.paddleSizeMultiplier;
      const opponentPaddleH = height * BASE_PADDLE_HEIGHT;
      const paddleW = width * PADDLE_WIDTH;
      
      const p1H = isPlayerRed ? playerPaddleH : opponentPaddleH;
      const p2H = !isPlayerRed ? playerPaddleH : opponentPaddleH;
      
      const drawPaddle = (x: number, y: number, w: number, h: number, color: string, style: 'SOLID' | 'GLOW' | 'OUTLINE') => {
        if (style === 'OUTLINE') {
          ctx.strokeStyle = color;
          ctx.lineWidth = 3;
          ctx.strokeRect(x, y, w, h);
        } else {
          ctx.fillStyle = color;
          if (style === 'GLOW') {
            ctx.shadowColor = color;
            ctx.shadowBlur = 25;
          }
          ctx.fillRect(x, y, w, h);
          ctx.shadowBlur = 0;
        }
      };
      
      const playerStyle = gameConfig.paddleStyle || 'GLOW';
      // Левая ракетка
      const p1Visible = !(cheats.invisibleOpponent && !isPlayerRed);
      if (p1Visible) {
        const p1Color = cheats.autoPlay && isPlayerRed ? '#ffd700' : '#ef4444';
        drawPaddle(10, state.player1Y * height - p1H / 2, paddleW, p1H, p1Color, playerStyle);
      }
      
      // Правая ракетка
      const p2Visible = !(cheats.invisibleOpponent && isPlayerRed);
      if (p2Visible) {
        const p2Color = cheats.autoPlay && !isPlayerRed ? '#ffd700' : '#3b82f6';
        drawPaddle(width - 10 - paddleW, state.player2Y * height - p2H / 2, paddleW, p2H, p2Color, playerStyle);
      }
      
      // Мяч
      const ballSizePixels = Math.max(8, width * BALL_SIZE_BASE * ballSize);
      ctx.fillStyle = '#ffffff';
      ctx.shadowColor = '#ffffff';
      ctx.shadowBlur = 20;
      ctx.beginPath();
      ctx.arc(state.ballX * width, state.ballY * height, ballSizePixels / 2, 0, Math.PI * 2);
      ctx.fill();
      ctx.shadowBlur = 0;

      // Траектория (чит + бустер)
      const allowBoostTrajectory = opponent === 'BOT';
      if (cheats.trajectoryPreview || cheats.ultraCheat || (cheats.trajectoryBoost && allowBoostTrajectory)) {
        const maxSegments = cheats.trajectoryBoost && allowBoostTrajectory
          ? Math.max(3, cheats.trajectoryCount || 3)
          : Math.max(1, cheats.trajectoryCount || 1);
        const passes = 1;
        for (let pass = 0; pass < passes; pass++) {
          const alpha = 0.7;
          ctx.strokeStyle = `rgba(0, 255, 255, ${alpha})`;
          ctx.lineWidth = 2.5;
          ctx.beginPath();
          let simX = state.ballX;
          let simY = state.ballY;
          let simVX = state.ballVX;
          let simVY = state.ballVY;
          ctx.moveTo(simX * width, simY * height);

          let segments = 0;
          const steps = 600 + maxSegments * 200;

          for (let i = 0; i < steps; i++) {
            simX += simVX;
            simY += simVY;

            if (simY <= BALL_SIZE_BASE / 2 || simY >= 1 - BALL_SIZE_BASE / 2) {
              simVY = -simVY;
              simY = Math.max(BALL_SIZE_BASE / 2, Math.min(1 - BALL_SIZE_BASE / 2, simY));
            }

            if (simX <= BALL_SIZE_BASE / 2 || simX >= 1 - BALL_SIZE_BASE / 2) {
              simVX = -simVX;
              simX = Math.max(BALL_SIZE_BASE / 2, Math.min(1 - BALL_SIZE_BASE / 2, simX));
              segments += 1;
              if (segments >= maxSegments) {
                ctx.lineTo(simX * width, simY * height);
                break;
              }
            }

            ctx.lineTo(simX * width, simY * height);
          }
          ctx.stroke();
        }
      }
      
      // Индикаторы читов
      if (!cheats.hideCheatUI) {
        let indicatorY = 20;
        ctx.font = 'bold 12px monospace';
        
        if (cheats.autoPlay) {
          ctx.fillStyle = '#ffd700';
          ctx.fillText('🤖 РЕЖИМ БОГА', 10, indicatorY);
          indicatorY += 15;
        }
        if (cheats.glitchMode) {
          ctx.fillStyle = '#ff00ff';
          ctx.fillText('⚡ ГЛИТЧ', 10, indicatorY);
          indicatorY += 15;
        }
        if (cheats.paddleSizeMultiplier > 1) {
          ctx.fillStyle = '#00ff00';
          ctx.fillText(`📏 x${cheats.paddleSizeMultiplier.toFixed(1)}`, 10, indicatorY);
          indicatorY += 15;
        }
        if (cheats.slowMotion) {
          ctx.fillStyle = '#00ffff';
          ctx.fillText('🐢 ЗАМЕДЛЕНИЕ', 10, indicatorY);
          indicatorY += 15;
        }
        if (cheats.magneticPaddle) {
          ctx.fillStyle = '#ff6600';
          ctx.fillText('🧲 МАГНИТ', 10, indicatorY);
        }
      }

      animationRef.current = requestAnimationFrame(gameLoop);
    };

    gameLoop();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [dimensions, isPaused, gameOver, opponent, playerSide, difficulty, gameConfig, predictBallY, ballSize, onUpdateStats]);

  // Обработка ввода
  useEffect(() => {
    (window as any).__cheatThumbScale = cheatConfig.controlThumbScale ?? 1;
  }, [cheatConfig.controlThumbScale]);

  const handleMoveLeft = useCallback((pos: number) => {
    inputRef.current.player1 = pos;
  }, []);

  const handleMoveRight = useCallback((pos: number) => {
    inputRef.current.player2 = pos;
  }, []);

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      containerRef.current?.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  const handleReset = () => {
    setBallSize(1);
    setShowSettings(false);
  };

  return (
    <div ref={containerRef} className="w-full h-screen bg-slate-950 flex flex-col">
      {/* Верхняя панель */}
      <div className="flex justify-between items-center p-2 bg-slate-900/80">
        <button onClick={onExit} className="p-2 text-slate-400 hover:text-white">
          <Home size={20} />
        </button>
        
        <div className="flex items-center gap-4">
          <span className="text-red-500 font-bold text-2xl">{scores.player1}</span>
          <span className="text-slate-500">:</span>
          <span className="text-blue-500 font-bold text-2xl">{scores.player2}</span>
        </div>
        
        <div className="flex gap-2">
          <button onClick={() => setIsMuted(!isMuted)} className="p-2 text-slate-400 hover:text-white">
            {isMuted ? <VolumeX size={20} /> : <Volume2 size={20} />}
          </button>
          <button onClick={() => setIsPaused(!isPaused)} className="p-2 text-slate-400 hover:text-white">
            {isPaused ? <Play size={20} /> : <Pause size={20} />}
          </button>
          <button onClick={() => setShowSettings(true)} className="p-2 text-slate-400 hover:text-white">
            <Settings size={20} />
          </button>
          <button onClick={toggleFullscreen} className="p-2 text-slate-400 hover:text-white">
            {isFullscreen ? <Minimize2 size={20} /> : <Maximize2 size={20} />}
          </button>
        </div>
      </div>
      
      {/* Игровое поле */}
      <div className="flex-1 relative">
        <canvas ref={canvasRef} className="w-full h-full" />
        
        {/* Пауза */}
        {isPaused && (
          <div className="absolute inset-0 bg-black/80 flex items-center justify-center">
            <div className="text-center">
              <h2 className="text-4xl font-bold text-white mb-4">ПАУЗА</h2>
              <button 
                onClick={() => setIsPaused(false)}
                className="px-8 py-3 bg-cyan-500 text-black font-bold rounded-lg"
              >
                ПРОДОЛЖИТЬ
              </button>
            </div>
          </div>
        )}
        
        {/* Конец игры */}
        {gameOver && (
          <div className="absolute inset-0 bg-black/80 flex items-center justify-center">
            <div className="text-center">
              <h2 className="text-4xl font-bold text-white mb-4">
                {winner === 'player1' ? '🔴 КРАСНЫЕ' : '🔵 СИНИЕ'} ПОБЕДИЛИ!
              </h2>
              <button 
                onClick={onExit}
                className="px-8 py-3 bg-cyan-500 text-black font-bold rounded-lg"
              >
                В МЕНЮ
              </button>
            </div>
          </div>
        )}
      </div>
      
      {/* Управление */}
      <GameControls
        opponent={opponent}
        playerSide={playerSide}
        onMoveLeft={handleMoveLeft}
        onMoveRight={handleMoveRight}
        isMultiplayer={multiplayerRole !== 'NONE'}
      />
      
      {/* Настройки */}
      {showSettings && (
        <SettingsModal
          isOpen={showSettings}
          onClose={() => setShowSettings(false)}
          ballSizeMultiplier={ballSize}
          onBallSizeChange={setBallSize}
          arenaTheme={arenaTheme}
          onArenaThemeChange={setArenaTheme}
          onReset={handleReset}
          getThemeLabel={(theme) => {
            switch (theme) {
              case 'NEON':
                return 'Неон';
              case 'CLASSIC':
                return 'Классика';
              case 'GRID':
                return 'Сетка';
              case 'SUNSET':
                return 'Закат';
              case 'ICE':
                return 'Лед';
              case 'VOID':
                return 'Пустота';
              case 'AUTUMN':
                return 'Осень';
              case 'WINTER':
                return 'Зима';
              case 'ROYAL':
                return 'Королевская';
              default:
                return theme;
            }
          }}
        />
      )}
    </div>
  );
};
