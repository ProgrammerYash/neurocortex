import { T } from './tokens.js';

export const PET_TYPES = {
  fox:   { name:"Brain Fox",   emoji:"🦊", color:T.orange, desc:"Clever & quick-thinking" },
  owl:   { name:"Study Owl",   emoji:"🦉", color:T.purple, desc:"Wise & observant" },
  cat:   { name:"Neuro Cat",   emoji:"🐱", color:T.teal,   desc:"Curious & focused" },
  dragon:{ name:"Cortex Dragon",emoji:"🐉",color:T.blue,   desc:"Powerful & resilient" },
};

export const ACHIEVEMENTS_DEF = [
  {id:"first_session",  name:"Research Pioneer",    desc:"Complete your first session",      emoji:"🔬", condition:g=>g.totalDays>=1},
  {id:"streak_3",       name:"3-Day Streak",         desc:"Complete 3 days in a row",         emoji:"🔥", condition:g=>g.streak>=3},
  {id:"streak_7",       name:"Week Warrior",         desc:"Complete 7 days in a row",         emoji:"⚡", condition:g=>g.streak>=7},
  {id:"streak_14",      name:"Fortnight Focus",      desc:"14-day streak achieved",           emoji:"💎", condition:g=>g.streak>=14},
  {id:"streak_30",      name:"Monthly Master",       desc:"30-day streak achieved",           emoji:"👑", condition:g=>g.streak>=30},
  {id:"total_7",        name:"One Week Complete",    desc:"7 total study days",               emoji:"📅", condition:g=>g.totalDays>=7},
  {id:"total_30",       name:"Monthly Completionist",desc:"30 total study days",              emoji:"🏆", condition:g=>g.totalDays>=30},
  {id:"coins_100",      name:"NeuroRich",            desc:"Earn 100 NeuroCoins",              emoji:"🪙", condition:g=>g.coins>=100},
  {id:"pet_level_5",    name:"Growing Together",     desc:"Pet reaches level 5",              emoji:"🌱", condition:g=>g.pet.level>=5},
  {id:"pet_level_10",   name:"Evolved Companion",    desc:"Pet reaches level 10",             emoji:"✨", condition:g=>g.pet.level>=10},
];

export const BRAIN_REGIONS = [
  {id:"prefrontal",  name:"Prefrontal Cortex",  desc:"Planning & Decision Making", color:T.teal},
  {id:"hippocampus", name:"Hippocampus",         desc:"Memory Formation",           color:T.purple},
  {id:"amygdala",    name:"Amygdala",            desc:"Emotional Regulation",       color:T.orange},
  {id:"parietal",    name:"Parietal Lobe",       desc:"Attention & Perception",     color:T.blue},
  {id:"temporal",    name:"Temporal Lobe",       desc:"Language & Memory",          color:T.green},
  {id:"cerebellum",  name:"Cerebellum",          desc:"Motor Learning & Timing",    color:T.gold},
];

export const HOUSE_ITEMS = [
  {id:"couch",     name:"Study Couch",   cost:50,  emoji:"🛋️"},
  {id:"desk",      name:"Research Desk", cost:75,  emoji:"🪑"},
  {id:"shelf",     name:"Bookshelf",     cost:60,  emoji:"📚"},
  {id:"plant",     name:"Neuron Plant",  cost:30,  emoji:"🌿"},
  {id:"lamp",      name:"Focus Lamp",    cost:40,  emoji:"💡"},
  {id:"poster",    name:"Brain Poster",  cost:45,  emoji:"🧠"},
  {id:"rug",       name:"Synapse Rug",   cost:55,  emoji:"🔵"},
  {id:"globe",     name:"Neural Globe",  cost:100, emoji:"🌐"},
];
