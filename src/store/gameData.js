import { PET_TYPES } from '../constants/gamification.js';

export const initGameData = (petChoice) => {
  const k = (petChoice && PET_TYPES[petChoice]) ? petChoice : "fox";
  return {
    pet: { type:k, name:PET_TYPES[k].name, happiness:80, energy:90, xp:0, level:1, evolution:"baby" },
    coins:0, streak:0, longestStreak:0, totalDays:0, lastCompleted:null,
    house:{ wallpaper:"default", items:[] },
    achievements:[], unlockedRegions:["prefrontal"],
    milestones:[],
  };
};
