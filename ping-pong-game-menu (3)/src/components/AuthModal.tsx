import React, { useState } from 'react';
import { X, User, Mail, Lock, LogIn, UserPlus } from 'lucide-react';
import { AuthService } from '../services/auth';
import { User as UserType } from '../types';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onLogin: (user: UserType) => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose, onLogin }) => {
  const [isRegister, setIsRegister] = useState(false);
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (isRegister) {
      if (!username || !email || !password) {
        setError('All fields are required');
        return;
      }
      const result = AuthService.register(username, email, password);
      if ('error' in result) {
        setError(result.error);
      } else {
        onLogin(result);
        onClose();
      }
    } else {
      if (!email || !password) {
        setError('Email and Password are required');
        return;
      }
      const result = AuthService.login(email, password);
      if ('error' in result) {
        setError(result.error);
      } else {
        onLogin(result);
        onClose();
      }
    }
  };

  return (
    <div className="fixed inset-0 z-[150] flex items-center justify-center bg-black/80 backdrop-blur-sm animate-in fade-in">
      <div className="w-full max-w-md bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl overflow-hidden relative animate-in zoom-in-95">
        <button 
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-white transition-colors"
        >
          <X size={24} />
        </button>

        <div className="p-8">
          <h2 className="text-3xl font-bold text-white mb-2 text-center">
            {isRegister ? 'Create Account' : 'Welcome Back'}
          </h2>
          <p className="text-slate-400 text-center mb-8">
            {isRegister ? 'Join the neon revolution' : 'Login to save your progress'}
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            {isRegister && (
              <div className="space-y-2">
                <label className="text-slate-300 text-sm font-bold ml-1">Username</label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
                  <input 
                    type="text" 
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl py-3 pl-10 pr-4 text-white focus:border-cyan-500 focus:outline-none transition-colors"
                    placeholder="Neo"
                  />
                </div>
              </div>
            )}

            <div className="space-y-2">
              <label className="text-slate-300 text-sm font-bold ml-1">Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
                <input 
                  type="email" 
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl py-3 pl-10 pr-4 text-white focus:border-cyan-500 focus:outline-none transition-colors"
                  placeholder="neo@matrix.com"
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-slate-300 text-sm font-bold ml-1">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
                <input 
                  type="password" 
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl py-3 pl-10 pr-4 text-white focus:border-cyan-500 focus:outline-none transition-colors"
                  placeholder="••••••••"
                />
              </div>
            </div>

            {error && (
              <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm text-center font-bold">
                {error}
              </div>
            )}

            <button 
              type="submit"
              className="w-full py-4 mt-4 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-bold rounded-xl shadow-lg transition-all transform hover:scale-[1.02] flex items-center justify-center gap-2"
            >
              {isRegister ? <UserPlus size={20} /> : <LogIn size={20} />}
              {isRegister ? 'REGISTER' : 'LOGIN'}
            </button>
          </form>

          <div className="mt-6 text-center">
            <button 
              type="button"
              onClick={() => { setIsRegister(!isRegister); setError(null); }}
              className="text-slate-400 hover:text-white underline decoration-slate-600 hover:decoration-white transition-all text-sm"
            >
              {isRegister ? 'Already have an account? Login' : "Don't have an account? Register"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
