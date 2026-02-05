import { Peer, DataConnection } from 'peerjs';
import { MultiplayerData } from '../types';

// Helper to generate a 6-digit code
const generateRoomCode = () => {
  return Math.floor(100000 + Math.random() * 900000).toString();
};

export class PeerService {
  private peer: Peer | null = null;
  private conn: DataConnection | null = null;
  private onDataCallback: ((data: MultiplayerData) => void) | null = null;
  private onConnectCallback: (() => void) | null = null;
  
  // Initialize as Host
  public async hostGame(): Promise<string> {
    return new Promise((resolve, reject) => {
      const roomCode = generateRoomCode();
      const peerId = `neon-pong-game-${roomCode}`;
      
      this.peer = new Peer(peerId);

      this.peer.on('open', (id) => {
        console.log('My peer ID is: ' + id);
        resolve(roomCode);
      });

      this.peer.on('connection', (conn) => {
        this.conn = conn;
        this.setupConnection();
        if (this.onConnectCallback) this.onConnectCallback();
      });

      this.peer.on('error', (err) => {
        console.error('Peer error:', err);
        reject(err);
      });
    });
  }

  // Join as Client
  public async joinGame(roomCode: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const peerId = `neon-pong-player-${generateRoomCode()}`; // Random ID for the joiner
      this.peer = new Peer(peerId);

      this.peer.on('open', () => {
        const hostId = `neon-pong-game-${roomCode}`;
        const conn = this.peer!.connect(hostId);
        
        conn.on('open', () => {
          this.conn = conn;
          this.setupConnection();
          if (this.onConnectCallback) this.onConnectCallback();
          resolve();
        });

        conn.on('error', (err) => {
          reject(err);
        });
      });

      this.peer.on('error', (err) => {
        reject(err);
      });
    });
  }

  private setupConnection() {
    if (!this.conn) return;

    this.conn.on('data', (data: any) => {
      if (this.onDataCallback) {
        this.onDataCallback(data as MultiplayerData);
      }
    });

    this.conn.on('close', () => {
      console.log('Connection closed');
      // Handle disconnect
    });
  }

  public send(data: MultiplayerData) {
    if (this.conn && this.conn.open) {
      this.conn.send(data);
    }
  }

  public onData(callback: (data: MultiplayerData) => void) {
    this.onDataCallback = callback;
  }

  public onConnect(callback: () => void) {
    this.onConnectCallback = callback;
  }

  public destroy() {
    if (this.conn) this.conn.close();
    if (this.peer) this.peer.destroy();
  }
}

export const peerService = new PeerService();

