import { io, Socket } from 'socket.io-client';

interface RoomConfig {
  winCondition: 'SCORE' | 'TIME';
  winValue: number;
  arenaTheme: 'NEON' | 'CLASSIC' | 'GRID' | 'SUNSET' | 'ICE' | 'VOID';
}

interface RoomInfo {
  code: string;
  hostName: string;
  roomName: string;
  hasPassword: boolean;
  players: number;
  config?: RoomConfig;
}

const SERVER_URL = (window as any).__NEON_SERVER_URL || 'http://localhost:3001';

class SocketService {
  private socket: Socket | null = null;
  private roomCode: string | null = null;

  connect() {
    if (this.socket) return this.socket;
    this.socket = io(SERVER_URL, {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: 10,
      reconnectionDelay: 500,
      timeout: 5000
    });
    return this.socket;
  }

  async ensureConnected(): Promise<Socket> {
    const socket = this.connect();
    if (socket.connected) return socket;
    return new Promise((resolve, reject) => {
      const onConnect = () => {
        socket.off('connect_error', onError);
        resolve(socket);
      };
      const onError = (err: any) => {
        socket.off('connect', onConnect);
        reject(err);
      };
      socket.once('connect', onConnect);
      socket.once('connect_error', onError);
    });
  }

  getRoomCode() {
    return this.roomCode;
  }

  async createRoom(payload: { hostName: string; roomName: string; password?: string; config: RoomConfig; }): Promise<RoomInfo> {
    const socket = await this.ensureConnected();
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error('Create timeout')), 3000);
      socket.emit('room:create', payload, (res: any) => {
        clearTimeout(timeout);
        if (!res?.ok) {
          reject(new Error(res?.message || 'Create failed'));
          return;
        }
        this.roomCode = res.room.code;
        resolve(res.room);
      });
    });
  }

  async joinRoom(payload: { code: string; password?: string }): Promise<RoomInfo> {
    const socket = await this.ensureConnected();
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error('Join timeout')), 3000);
      socket.emit('room:join', payload, (res: any) => {
        clearTimeout(timeout);
        if (!res?.ok) {
          reject(new Error(res?.message || 'Join failed'));
          return;
        }
        this.roomCode = res.room.code;
        resolve(res.room);
      });
    });
  }

  async listRooms(): Promise<RoomInfo[]> {
    const socket = await this.ensureConnected();
    return new Promise((resolve) => {
      socket.emit('room:list', {}, (rooms: RoomInfo[]) => {
        resolve(rooms || []);
      });
    });
  }

  onRoomReady(cb: (config: RoomConfig) => void) {
    const socket = this.connect();
    socket.off('room:ready');
    socket.on('room:ready', (payload: { config: RoomConfig }) => {
      cb(payload?.config);
    });
  }

  onRoomClosed(cb: () => void) {
    const socket = this.connect();
    socket.off('room:closed');
    socket.on('room:closed', cb);
  }

  onConnect(cb: () => void) {
    const socket = this.connect();
    socket.off('connect');
    socket.on('connect', cb);
  }

  onConnectError(cb: (err: any) => void) {
    const socket = this.connect();
    socket.off('connect_error');
    socket.on('connect_error', cb);
  }

  sendGameUpdate(data: any) {
    if (!this.roomCode) return;
    const socket = this.connect();
    socket.emit('game:update', { code: this.roomCode, data });
  }

  onGameUpdate(cb: (data: any) => void) {
    const socket = this.connect();
    socket.off('game:update');
    socket.on('game:update', cb);
  }
}

export const socketService = new SocketService();
export type { RoomInfo, RoomConfig };
