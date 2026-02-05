import React, { useEffect, useState } from 'react';
import { translations, Language } from '../i18n/translations';
import { User, MultiplayerRole, GameConfig } from '../types';
import { Lock, Copy, ArrowLeft, Search, Plus, Key, Radio, RefreshCw } from 'lucide-react';
import { socketService, RoomInfo, RoomConfig } from '../services/socket';
import { soundManager } from '../utils/sound';

interface OnlineLobbyProps {
  language: Language;
  user: User | null;
  onBack: () => void;
  onRegisterClick: () => void;
  onGameStart: (role: MultiplayerRole, config: GameConfig) => void;
}

export const OnlineLobby: React.FC<OnlineLobbyProps> = ({ 
  language, 
  user, 
  onBack,
  onRegisterClick,
  onGameStart
}) => {
  const t = translations[language];
  
  const [view, setView] = useState<'LIST' | 'CREATE' | 'WAITING' | 'JOIN_CODE'>('LIST');
  const [myRoomCode, setMyRoomCode] = useState('');
  const [joinCodeInput, setJoinCodeInput] = useState('');
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hostName, setHostName] = useState('');
  const [roomName, setRoomName] = useState('');
  const [roomPassword, setRoomPassword] = useState('');
  const [joinPassword, setJoinPassword] = useState('');
  const [winPreset, setWinPreset] = useState<10 | 20 | 30 | 50>(10);
  const [winCondition, setWinCondition] = useState<'SCORE' | 'TIME'>('SCORE');
  const [arenaTheme, setArenaTheme] = useState<'NEON' | 'CLASSIC' | 'GRID' | 'SUNSET' | 'ICE' | 'VOID'>('NEON');
  const [rooms, setRooms] = useState<RoomInfo[]>([]);
  const [search, setSearch] = useState('');

  useEffect(() => {
    socketService.connect();
    socketService.onConnect(() => setError(null));
    socketService.onConnectError(() => {
      setError('Сервер недоступен. Убедитесь, что server запущен на 3001.');
    });
    socketService.onRoomReady((config: RoomConfig) => {
      soundManager.playConnect();
      onGameStart('HOST', {
        winCondition: config.winCondition,
        winValue: config.winValue,
        arenaTheme: config.arenaTheme,
        paddleSizeMultiplier: 1,
      });
    });
    socketService.onGameUpdate(() => {});
  }, [onGameStart]);

  const refreshRooms = async () => {
    try {
      const list = await socketService.listRooms();
      setRooms(list);
    } catch {
      setRooms([]);
    }
  };

  useEffect(() => {
    if (view === 'LIST') {
      refreshRooms();
    }
  }, [view]);

  const handleOpenCreate = () => {
    setHostName('');
    setRoomName('');
    setRoomPassword('');
    setWinPreset(10);
    setWinCondition('SCORE');
    setArenaTheme('NEON');
    setView('CREATE');
  };

  const handleCreateRoom = async () => {
    if (!hostName.trim()) {
      setError('Введите имя');
      return;
    }
    setIsConnecting(true);
    setError(null);
    try {
      const config: RoomConfig = {
        winCondition,
        winValue: winPreset,
        arenaTheme
      };
      const room = await socketService.createRoom({
        hostName,
        roomName: roomName.trim() || hostName.trim(),
        password: roomPassword.trim() || undefined,
        config
      });
      setMyRoomCode(room.code);
      setView('WAITING');
      socketService.onRoomReady((readyConfig) => {
        soundManager.playConnect();
        onGameStart('HOST', {
          winCondition: readyConfig.winCondition,
          winValue: readyConfig.winValue,
          arenaTheme: readyConfig.arenaTheme,
          paddleSizeMultiplier: 1
        });
      });
    } catch (err: any) {
      setError(err?.message || 'Не удалось создать комнату. Проверьте сервер.');
    } finally {
      setIsConnecting(false);
    }
  };

  const handleJoinByCode = async () => {
    if (!joinCodeInput.trim()) return;

    setIsConnecting(true);
    setError(null);
    try {
      await socketService.joinRoom({
        code: joinCodeInput.trim(),
        password: joinPassword.trim() || undefined
      });
      socketService.onRoomReady((readyConfig) => {
        soundManager.playConnect();
        onGameStart('CLIENT', {
          winCondition: readyConfig.winCondition,
          winValue: readyConfig.winValue,
          arenaTheme: readyConfig.arenaTheme,
          paddleSizeMultiplier: 1
        });
      });
    } catch (err: any) {
      setError(err?.message || 'Не удалось подключиться. Проверьте код или пароль.');
    } finally {
      setIsConnecting(false);
    }
  };

  const copyCode = () => {
    navigator.clipboard.writeText(myRoomCode);
  };

  if (!user) {
    return (
      <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/90 backdrop-blur-xl p-6">
        <div className="bg-slate-900 border border-red-500/50 p-8 rounded-2xl shadow-[0_0_50px_rgba(239,68,68,0.3)] max-w-md w-full text-center relative overflow-hidden">
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-red-500 to-transparent animate-scan" />
          <Lock className="w-16 h-16 text-red-500 mx-auto mb-6 animate-pulse" />
          <h2 className="text-2xl font-black text-white mb-2 tracking-widest font-mono">{t.accessDenied}</h2>
          <p className="text-gray-400 mb-8 font-mono text-sm leading-relaxed">{t.registerRequired}</p>
          <div className="flex flex-col gap-3">
            <button
              onClick={onRegisterClick}
              className="w-full py-4 bg-gradient-to-r from-red-600 to-red-800 text-white font-bold rounded-lg hover:from-red-500 hover:to-red-700 transition-all transform hover:scale-[1.02] shadow-[0_0_20px_rgba(220,38,38,0.5)] font-mono tracking-widest"
            >
              {t.goRegister}
            </button>
            <button
              onClick={onBack}
              className="w-full py-3 bg-slate-800 text-gray-400 font-bold rounded-lg hover:bg-slate-700 transition-all font-mono"
            >
              {t.cancel}
            </button>
          </div>
        </div>
      </div>
    );
  }

  const filteredRooms = rooms.filter(room => {
    const value = `${room.roomName} ${room.hostName}`.toLowerCase();
    return value.includes(search.toLowerCase());
  });

  return (
    <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/95 backdrop-blur-md">
      <div className="w-full max-w-4xl h-[85vh] flex flex-col p-4 md:p-6">
        <div className="flex items-center justify-between mb-6 shrink-0">
          <button 
            onClick={view === 'LIST' ? onBack : () => setView('LIST')}
            className="p-3 bg-slate-800/50 hover:bg-white/10 rounded-full transition-colors text-white border border-white/10"
          >
            <ArrowLeft />
          </button>
          <h2 className="text-2xl md:text-3xl font-black text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-500 font-mono tracking-tighter">
            {t.onlineLobby}
          </h2>
          <div className="w-10" />
        </div>

        <div className="flex-1 bg-slate-900/80 border border-white/10 rounded-2xl shadow-2xl backdrop-blur-sm relative overflow-hidden flex flex-col">
          <div className="absolute inset-0 bg-grid-white/[0.02] bg-[length:20px_20px]" />

          {view === 'LIST' && (
            <div className="flex flex-col h-full relative z-10">
              <div className="p-4 border-b border-white/10 flex flex-col md:flex-row gap-4">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-5 h-5" />
                  <input 
                    type="text" 
                    placeholder={t.searchRooms}
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    className="w-full bg-black/40 border border-white/10 rounded-xl pl-10 pr-4 py-3 text-white placeholder-gray-500"
                  />
                </div>
                <div className="flex gap-2">
                  <button 
                    onClick={() => setView('JOIN_CODE')}
                    className="px-6 py-3 bg-slate-700 hover:bg-slate-600 text-white font-bold rounded-xl flex items-center justify-center gap-2 transition-all"
                  >
                    <Key className="w-5 h-5" />
                    {t.join} Code
                  </button>
                  <button 
                    onClick={handleOpenCreate}
                    className="px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white font-bold rounded-xl flex items-center justify-center gap-2 transition-all shadow-lg shadow-blue-600/20"
                  >
                    <Plus className="w-5 h-5" />
                    {t.create}
                  </button>
                  <button
                    onClick={refreshRooms}
                    className="px-4 py-3 bg-slate-800 text-white rounded-xl"
                  >
                    <RefreshCw className="w-5 h-5" />
                  </button>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto p-4 space-y-3">
                {filteredRooms.length === 0 && (
                  <div className="flex flex-col items-center justify-center text-center py-10">
                    <Radio className="w-16 h-16 text-gray-600 mb-4 animate-pulse" />
                    <h3 className="text-xl font-bold text-gray-400 mb-2">{t.noRoomsFound}</h3>
                    <p className="text-gray-600 max-w-sm">Создай комнату и поделись кодом с другом.</p>
                  </div>
                )}

                {filteredRooms.map(room => (
                  <button
                    key={room.code}
                    onClick={() => {
                      setJoinCodeInput(room.code);
                      setView('JOIN_CODE');
                    }}
                    className="w-full p-4 rounded-xl border border-slate-800 bg-slate-900/60 flex items-center justify-between hover:border-blue-400/60 transition-all"
                  >
                    <div className="text-left">
                      <div className="text-white font-bold">{room.roomName}</div>
                      <div className="text-slate-400 text-xs">Host: {room.hostName}</div>
                    </div>
                    <div className="flex items-center gap-2 text-slate-400 text-xs">
                      {room.hasPassword && <Lock size={14} />}
                      <span>{room.players}/2</span>
                      <span className="font-mono">#{room.code}</span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {view === 'WAITING' && (
            <div className="flex-1 flex flex-col items-center justify-center p-6 relative z-10 text-center">
              <div className="relative inline-block mb-8">
                <div className="w-24 h-24 rounded-full border-4 border-t-blue-500 border-r-blue-500 border-b-transparent border-l-transparent animate-spin mx-auto" />
                <div className="absolute inset-0 flex items-center justify-center font-mono text-sm text-blue-400 font-bold animate-pulse">
                  WAITING
                </div>
              </div>
              <h3 className="text-2xl font-bold text-white mb-2">{t.waitingForOpponent}</h3>
              <div 
                onClick={copyCode}
                className="inline-flex items-center gap-3 bg-black/50 px-8 py-6 rounded-2xl border border-blue-500/30 hover:border-blue-500 hover:bg-blue-500/10 transition-all cursor-pointer group mt-4 mb-8"
              >
                <div className="text-left">
                  <div className="text-xs text-gray-500 uppercase tracking-widest mb-1">{t.roomId}</div>
                  <div className="text-4xl font-mono text-white font-black tracking-widest">{myRoomCode}</div>
                </div>
                <Copy className="w-6 h-6 text-gray-500 group-hover:text-white transition-colors" />
              </div>
              <div className="text-sm text-gray-400 max-w-xs mx-auto">Поделись кодом, чтобы друг вошёл.</div>
              <button onClick={() => setView('LIST')} className="mt-8 text-gray-600 hover:text-white">{t.cancel}</button>
            </div>
          )}

          {view === 'CREATE' && (
            <div className="flex-1 flex flex-col items-center justify-start p-6 relative z-10 overflow-y-auto touch-pan-y">
              <div className="w-full max-w-lg space-y-6 pb-6">
                <h3 className="text-2xl font-bold text-white text-center">{t.createRoomTitle}</h3>

                <div className="space-y-4">
                  <div>
                    <label className="text-slate-400 text-xs font-bold tracking-widest uppercase">{t.hostName}</label>
                    <input
                      type="text"
                      value={hostName}
                      onChange={(e) => setHostName(e.target.value)}
                      className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-white focus:border-blue-500 outline-none"
                      placeholder="Neo"
                    />
                  </div>

                  <div>
                    <label className="text-slate-400 text-xs font-bold tracking-widest uppercase">{t.roomNameOptional}</label>
                    <input
                      type="text"
                      value={roomName}
                      onChange={(e) => setRoomName(e.target.value)}
                      className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-white focus:border-blue-500 outline-none"
                      placeholder="Pong Arena"
                    />
                  </div>

                  <div>
                    <label className="text-slate-400 text-xs font-bold tracking-widest uppercase">{t.passwordOptional}</label>
                    <input
                      type="password"
                      value={roomPassword}
                      onChange={(e) => setRoomPassword(e.target.value)}
                      className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-white focus:border-blue-500 outline-none"
                      placeholder="••••••"
                    />
                  </div>
                </div>

                <div className="border-t border-white/10 pt-6">
                  <h4 className="text-slate-300 font-bold mb-3">{t.matchSettings}</h4>
                  <div className="flex gap-2 mb-4">
                    {[10, 20, 30, 50].map((value) => (
                      <button
                        key={value}
                        onClick={() => { setWinPreset(value as 10 | 20 | 30 | 50); setWinCondition('SCORE'); }}
                        className={`px-4 py-2 rounded-lg font-bold ${winPreset === value && winCondition === 'SCORE' ? 'bg-blue-500 text-black' : 'bg-slate-800 text-slate-300'}`}
                      >
                        {value} {t.score}
                      </button>
                    ))}
                  </div>

                  <div className="flex gap-2">
                    {['NEON', 'CLASSIC', 'GRID', 'SUNSET', 'ICE', 'VOID'].map((theme) => (
                      <button
                        key={theme}
                        onClick={() => setArenaTheme(theme as 'NEON' | 'CLASSIC' | 'GRID' | 'SUNSET' | 'ICE' | 'VOID')}
                        className={`px-4 py-2 rounded-lg font-bold ${arenaTheme === theme ? 'bg-purple-500 text-black' : 'bg-slate-800 text-slate-300'}`}
                      >
                        {theme}
                      </button>
                    ))}
                  </div>
                </div>

                {error && <p className="text-red-500 text-sm font-bold text-center">{error}</p>}

                <button
                  onClick={handleCreateRoom}
                  disabled={isConnecting}
                  className="w-full py-4 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white font-bold rounded-xl transition-all shadow-lg shadow-blue-900/20"
                >
                  {isConnecting ? 'CREATING... (<=3s)' : t.createRoom}
                </button>
              </div>
            </div>
          )}

          {view === 'JOIN_CODE' && (
            <div className="flex-1 flex flex-col items-center justify-center p-6 relative z-10">
              <div className="w-full max-w-md space-y-6 text-center">
                <h3 className="text-xl font-bold text-white mb-6">{t.joinRoomTitle}</h3>
                <input 
                  type="text" 
                  value={joinCodeInput}
                  onChange={(e) => setJoinCodeInput(e.target.value.replace(/[^0-9]/g, '').slice(0, 6))}
                  className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-6 text-center text-3xl font-mono tracking-[0.5em] text-white focus:border-blue-500 outline-none"
                  placeholder="000000"
                />
                <input
                  type="password"
                  value={joinPassword}
                  onChange={(e) => setJoinPassword(e.target.value)}
                  className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-white focus:border-blue-500 outline-none"
                  placeholder={t.joinPassword}
                />
                {error && <p className="text-red-500 text-sm font-bold animate-bounce">{error}</p>}
                <button 
                  onClick={handleJoinByCode}
                  disabled={joinCodeInput.length < 6 || isConnecting}
                  className="w-full py-4 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white font-bold rounded-xl transition-all shadow-lg shadow-blue-900/20 disabled:opacity-50 disabled:cursor-not-allowed mt-4"
                >
                  {isConnecting ? 'CONNECTING...' : t.joinRoom}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
