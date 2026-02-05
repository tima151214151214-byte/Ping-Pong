import { User } from '../types';

const USERS_KEY = 'neon_pong_users';
const CURRENT_USER_KEY = 'neon_pong_current_user';

export const AuthService = {
  getUsers: (): User[] => {
    try {
      const data = localStorage.getItem(USERS_KEY);
      return data ? JSON.parse(data) : [];
    } catch (e) {
      console.error("Failed to parse users", e);
      return [];
    }
  },

  saveUsers: (users: User[]) => {
    localStorage.setItem(USERS_KEY, JSON.stringify(users));
  },

  register: (username: string, email: string, password: string): User | { error: string } => {
    const users = AuthService.getUsers();
    if (users.find(u => u.email === email)) return { error: 'Email already exists' };
    if (users.find(u => u.username === username)) return { error: 'Username already exists' };

    const newUser: User = {
      id: crypto.randomUUID(),
      username,
      email,
      passwordHash: password, // Simple storage for demo
      achievements: [],
      stats: { totalWins: 0, totalLosses: 0, totalExits: 0, totalGamesPlayed: 0, totalScore: 0, maxRally: 0, level: 0, coins: 0 }
    };

    users.push(newUser);
    AuthService.saveUsers(users);
    
    // Auto login
    localStorage.setItem(CURRENT_USER_KEY, JSON.stringify(newUser.id));
    return newUser;
  },

  login: (email: string, password: string): User | { error: string } => {
    const users = AuthService.getUsers();
    const user = users.find(u => u.email === email && u.passwordHash === password);
    if (!user) return { error: 'Invalid credentials' };
    
    // Update local storage to remember this user
    localStorage.setItem(CURRENT_USER_KEY, JSON.stringify(user.id));
    return user;
  },

  logout: () => {
    localStorage.removeItem(CURRENT_USER_KEY);
  },

  getCurrentUser: (): User | null => {
    try {
      const stored = localStorage.getItem(CURRENT_USER_KEY);
      if (!stored) return null;
      const id = JSON.parse(stored); // ID might be stored as string or JSON string
      const users = AuthService.getUsers();
      return users.find(u => u.id === id) || null;
    } catch (e) {
      return null;
    }
  },

  updateUser: (user: User) => {
    const users = AuthService.getUsers();
    const index = users.findIndex(u => u.id === user.id);
    if (index !== -1) {
      users[index] = user;
      AuthService.saveUsers(users);
    }
  }
};
