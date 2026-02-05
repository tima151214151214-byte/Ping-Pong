export interface Achievement {
  id: string;
  title: string;
  description: string;
  icon: string;
  isUnlocked: boolean;
  category: 'bronze' | 'silver' | 'gold' | 'platinum' | 'secret';
}

export const generateAchievements = (): Achievement[] => {
  const achievements: Achievement[] = [];

  // 1. Win Streaks & Counts
  const winMilestones = [1, 5, 10, 25, 50, 100, 200, 500, 1000];
  winMilestones.forEach(count => {
    achievements.push({
      id: `win_${count}`,
      title: `Winner ${count}`,
      description: `Win ${count} matches.`,
      icon: '🏆',
      isUnlocked: false,
      category: count < 50 ? 'bronze' : count < 200 ? 'silver' : 'gold'
    });
  });

  // 2. Score Counters
  const scoreMilestones = [10, 50, 100, 500, 1000, 5000, 10000];
  scoreMilestones.forEach(count => {
    achievements.push({
      id: `score_${count}`,
      title: `Scorer ${count}`,
      description: `Score a total of ${count} points.`,
      icon: '⚽',
      isUnlocked: false,
      category: count < 500 ? 'bronze' : count < 5000 ? 'silver' : 'gold'
    });
  });

  // 3. Difficulty Specific
  achievements.push(
    { id: 'beat_easy', title: 'Baby Steps', description: 'Beat the Easy Bot.', icon: '👶', isUnlocked: false, category: 'bronze' },
    { id: 'beat_medium', title: 'Competitor', description: 'Beat the Medium Bot.', icon: '🤖', isUnlocked: false, category: 'silver' },
    { id: 'beat_hard', title: 'Pro Slayer', description: 'Beat the Hard Bot.', icon: '⚔️', isUnlocked: false, category: 'gold' },
    { id: 'beat_impossible', title: 'God Slayer', description: 'Beat the Impossible Bot (Good Luck).', icon: '☠️', isUnlocked: false, category: 'platinum' },
    { id: 'clean_sheet', title: 'The Wall', description: 'Win a game without letting the opponent score (10-0).', icon: '🛡️', isUnlocked: false, category: 'gold' },
    { id: 'close_call', title: 'Clutch', description: 'Win a game with score 10-9.', icon: '😅', isUnlocked: false, category: 'silver' },
    { id: 'comeback', title: 'Comeback King', description: 'Win after being down by 5 points.', icon: '👑', isUnlocked: false, category: 'gold' },
    { id: 'rally_20', title: 'Tennis Player', description: 'Keep the ball alive for 20 hits.', icon: '🎾', isUnlocked: false, category: 'bronze' },
    { id: 'rally_50', title: 'Marathon', description: 'Keep the ball alive for 50 hits.', icon: '🏃', isUnlocked: false, category: 'silver' },
    { id: 'rally_100', title: 'Matrix', description: 'Keep the ball alive for 100 hits.', icon: '🕶️', isUnlocked: false, category: 'gold' }
  );

  // 4. Secret / Dev Achievements
  achievements.push(
    { id: 'dev_mode', title: 'Hacker', description: 'Unlock Developer Mode.', icon: '💻', isUnlocked: false, category: 'secret' },
    { id: 'admin_mode', title: 'Admin', description: 'Unlock Admin Mode.', icon: '🔑', isUnlocked: false, category: 'secret' },
    { id: 'cheater', title: 'Dirty Play', description: 'Use a cheat code.', icon: '🚫', isUnlocked: false, category: 'secret' },
    { id: 'huge_paddle', title: 'Compensating?', description: 'Play with a 5x Paddle.', icon: '🧱', isUnlocked: false, category: 'secret' },
    { id: 'tiny_ball', title: 'Sniper', description: 'Win with the smallest ball size.', icon: '🎯', isUnlocked: false, category: 'platinum' },
    { id: 'level_1', title: 'Первый уровень', description: 'Достичь 1 уровня.', icon: '⭐', isUnlocked: false, category: 'bronze' },
    { id: 'level_10', title: 'Опытный игрок', description: 'Достичь 10 уровня.', icon: '🏅', isUnlocked: false, category: 'silver' },
    { id: 'level_50', title: 'Ветеран', description: 'Достичь 50 уровня.', icon: '🎖️', isUnlocked: false, category: 'gold' },
    { id: 'level_99', title: 'Порог мастера', description: 'Достичь 99 уровня.', icon: '👑', isUnlocked: false, category: 'gold' },
    { id: 'level_100', title: 'Легенда', description: 'Достичь 100 уровня.', icon: '🔥', isUnlocked: false, category: 'platinum' },
    { id: 'level_300', title: 'ПРОФЕССИОНАЛ', description: 'Получить 300 уровень и стать победителем.', icon: '🏆', isUnlocked: false, category: 'platinum' }
  );

  // 5. Extended "God Mode" Achievements (The requested 50+)
  const glitchTitles = ['Null Pointer', 'Buffer Overflow', 'Stack Trace', 'Segfault', 'Kernel Panic', 'Blue Screen', '404 Found', 'Syntax Error', 'Infinite Loop', 'Race Condition'];
  glitchTitles.forEach((title, i) => {
    achievements.push({
      id: `glitch_${i}`,
      title: title,
      description: 'Break the game boundaries.',
      icon: '👾',
      isUnlocked: false,
      category: 'secret'
    });
  });

  const timeWasterTitles = ['Watching Paint Dry', 'Still Here?', 'Go Outside', 'No Life', 'Dedicated', 'Obsessed', 'Addicted', 'Just One More', 'Sleep is for the Weak', 'Vampire'];
  timeWasterTitles.forEach((title, i) => {
    achievements.push({
      id: `time_${i}`,
      title: title,
      description: `Play for ${i + 1} hours (simulated).`,
      icon: '⏰',
      isUnlocked: false,
      category: 'bronze'
    });
  });

  const skillTitles = ['Spin Doctor', 'Angle Master', 'Geometry Dash', 'Physics Prof', 'Calculated', 'Simple Geometry', 'Prediction God', 'Oracle', 'Time Traveler', 'Chosen One'];
  skillTitles.forEach((title, i) => {
    achievements.push({
      id: `skill_${i}`,
      title: title,
      description: 'Perform an impossible shot.',
      icon: '🎱',
      isUnlocked: false,
      category: 'gold'
    });
  });

  const luckyTitles = ['Pure Luck', 'RNGesus', 'Dice Roll', 'Jackpot', 'Lottery Winner', 'Clover', 'Horseshoe', 'Rabbit Foot', 'Wishbone', 'Shooting Star'];
  luckyTitles.forEach((title, i) => {
    achievements.push({
      id: `luck_${i}`,
      title: title,
      description: 'Win a point you should have lost.',
      icon: '🍀',
      isUnlocked: false,
      category: 'silver'
    });
  });

  const trollTitles = ['U Mad?', 'Get Wrecked', 'Ez', 'Noob Down', 'Uninstall', 'Git Gud', 'Cry More', 'Salty', 'Rage Quit', 'Lag Switch'];
  trollTitles.forEach((title, i) => {
    achievements.push({
      id: `troll_${i}`,
      title: title,
      description: 'Troll the bot significantly.',
      icon: '🤪',
      isUnlocked: false,
      category: 'secret'
    });
  });

  // Fill generic levels to reach high count
  for (let i = 1; i <= 30; i++) {
    achievements.push({
      id: `mastery_${i}`,
      title: `Pong Master ${i}`,
      description: `Reach Mastery Level ${i}.`,
      icon: '🎖️',
      isUnlocked: false,
      category: 'bronze'
    });
  }

  // Auto-generate achievements up to 1000 total
  const categories: Achievement['category'][] = ['bronze', 'silver', 'gold', 'platinum', 'secret'];
  const icons = ['✨', '🔥', '⚡', '🧠', '🎯', '🧪', '🛰️', '🧊', '💎', '🧨'];
  let index = 1;
  while (achievements.length < 1000) {
    const category = categories[index % categories.length];
    const icon = icons[index % icons.length];
    achievements.push({
      id: `auto_${index}`,
      title: `Легенда ${index}`,
      description: `Секретное достижение #${index}.`,
      icon,
      isUnlocked: false,
      category
    });
    index += 1;
  }

  return achievements;
};
