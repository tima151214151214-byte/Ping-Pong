import express from 'express';
import http from 'http';
import { Server } from 'socket.io';
import { nanoid } from 'nanoid';

const app = express();
const server = http.createServer(app);
const io = new Server(server, {
  cors: {
    origin: '*',
    methods: ['GET', 'POST']
  }
});

const rooms = new Map();

const createRoom = ({ hostName, roomName, password, config }) => {
  const roomCode = nanoid(6).toUpperCase();
  const room = {
    code: roomCode,
    hostName,
    roomName,
    password: password || null,
    config,
    hostSocketId: null,
    clientSocketId: null,
    createdAt: Date.now()
  };
  rooms.set(roomCode, room);
  return room;
};

io.on('connection', (socket) => {
  socket.on('room:create', (payload, callback) => {
    try {
      const room = createRoom(payload);
      room.hostSocketId = socket.id;
      socket.join(room.code);
      callback({ ok: true, room: { code: room.code, hostName: room.hostName, roomName: room.roomName, hasPassword: !!room.password, config: room.config } });
    } catch (err) {
      callback({ ok: false, message: 'Failed to create room.' });
    }
  });

  socket.on('room:join', (payload, callback) => {
    const room = rooms.get(payload.code);
    if (!room) {
      callback({ ok: false, message: 'Room not found.' });
      return;
    }
    if (room.password && room.password !== payload.password) {
      callback({ ok: false, message: 'Wrong password.' });
      return;
    }
    if (room.clientSocketId) {
      callback({ ok: false, message: 'Room already full.' });
      return;
    }
    room.clientSocketId = socket.id;
    socket.join(room.code);
    io.to(room.code).emit('room:ready', { config: room.config });
    callback({ ok: true, room: { code: room.code, hostName: room.hostName, roomName: room.roomName, hasPassword: !!room.password, config: room.config } });
  });

  socket.on('room:list', (_, callback) => {
    const list = Array.from(rooms.values()).map(room => ({
      code: room.code,
      hostName: room.hostName,
      roomName: room.roomName,
      hasPassword: !!room.password,
      players: room.clientSocketId ? 2 : 1
    }));
    callback(list);
  });

  socket.on('game:update', (payload) => {
    if (!payload?.code) return;
    socket.to(payload.code).emit('game:update', payload.data);
  });

  socket.on('disconnect', () => {
    for (const [code, room] of rooms.entries()) {
      if (room.hostSocketId === socket.id || room.clientSocketId === socket.id) {
        io.to(code).emit('room:closed');
        rooms.delete(code);
      }
    }
  });
});

const PORT = process.env.PORT || 3001;
server.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});
