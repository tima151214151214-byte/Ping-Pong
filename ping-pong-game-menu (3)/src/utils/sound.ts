class SoundManagerClass {
  private ctx: AudioContext | null = null;
  private masterGain: GainNode | null = null;
  private muted: boolean = false;

  constructor() {
    this.init();
  }

  private init() {
    try {
      this.ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
      this.masterGain = this.ctx.createGain();
      this.masterGain.connect(this.ctx.destination);
      this.masterGain.gain.value = 0.3;
    } catch (e) {
      console.warn('Web Audio API not supported');
    }
  }

  public resume() {
    if (this.ctx && this.ctx.state === 'suspended') {
      this.ctx.resume();
    }
  }

  public setMuted(muted: boolean) {
    this.muted = muted;
    if (this.masterGain) {
      this.masterGain.gain.value = muted ? 0 : 0.3;
    }
  }

  private playTone(frequency: number, duration: number, type: OscillatorType = 'sine', attack: number = 0.01) {
    if (!this.ctx || !this.masterGain || this.muted) return;
    
    this.resume();
    
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    
    osc.type = type;
    osc.frequency.value = frequency;
    
    gain.gain.setValueAtTime(0, this.ctx.currentTime);
    gain.gain.linearRampToValueAtTime(0.5, this.ctx.currentTime + attack);
    gain.gain.exponentialRampToValueAtTime(0.01, this.ctx.currentTime + duration);
    
    osc.connect(gain);
    gain.connect(this.masterGain);
    
    osc.start();
    osc.stop(this.ctx.currentTime + duration);
  }

  public playHit() {
    this.playTone(600, 0.1, 'square', 0.005);
    setTimeout(() => this.playTone(800, 0.05, 'sine', 0.005), 20);
  }

  public playWall() {
    this.playTone(200, 0.15, 'triangle', 0.01);
  }

  public playScore() {
    this.playTone(523, 0.1, 'square', 0.01);
    setTimeout(() => this.playTone(659, 0.1, 'square', 0.01), 100);
    setTimeout(() => this.playTone(784, 0.2, 'square', 0.01), 200);
  }

  public playClick() {
    this.playTone(1000, 0.05, 'sine', 0.005);
  }

  public playHover() {
    this.playTone(1500, 0.02, 'sine', 0.002);
  }

  public playGlitch() {
    if (!this.ctx || !this.masterGain || this.muted) return;
    this.resume();
    
    const bufferSize = this.ctx.sampleRate * 0.1;
    const buffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
    const data = buffer.getChannelData(0);
    
    for (let i = 0; i < bufferSize; i++) {
      data[i] = Math.random() * 2 - 1;
    }
    
    const noise = this.ctx.createBufferSource();
    noise.buffer = buffer;
    
    const gain = this.ctx.createGain();
    gain.gain.setValueAtTime(0.3, this.ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, this.ctx.currentTime + 0.1);
    
    noise.connect(gain);
    gain.connect(this.masterGain);
    
    noise.start();
  }

  public playConnect() {
    this.playTone(440, 0.1, 'sine', 0.01);
    setTimeout(() => this.playTone(550, 0.1, 'sine', 0.01), 100);
    setTimeout(() => this.playTone(660, 0.15, 'sine', 0.01), 200);
    setTimeout(() => this.playTone(880, 0.3, 'sine', 0.01), 300);
  }

  public playDisconnect() {
    this.playTone(440, 0.15, 'sine', 0.01);
    setTimeout(() => this.playTone(330, 0.15, 'sine', 0.01), 150);
    setTimeout(() => this.playTone(220, 0.3, 'triangle', 0.01), 300);
  }

  public playWin() {
    const notes = [523, 659, 784, 1047];
    notes.forEach((freq, i) => {
      setTimeout(() => this.playTone(freq, 0.3, 'square', 0.01), i * 150);
    });
  }

  public playLose() {
    this.playTone(300, 0.3, 'sawtooth', 0.01);
    setTimeout(() => this.playTone(200, 0.5, 'sawtooth', 0.01), 300);
  }
}

export const soundManager = new SoundManagerClass();
