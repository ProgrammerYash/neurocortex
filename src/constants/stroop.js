export const STROOP_COLORS = [
  {name:"RED",hex:"#FC8181"},{name:"BLUE",hex:"#63B3ED"},{name:"GREEN",hex:"#68D391"},{name:"YELLOW",hex:"#F6E05E"},{name:"PURPLE",hex:"#A78BFA"}
];
export const genStroop = (n=15) => Array.from({length:n},()=>{
  const word=STROOP_COLORS[Math.floor(Math.random()*STROOP_COLORS.length)];
  const ink=STROOP_COLORS[Math.floor(Math.random()*STROOP_COLORS.length)];
  return {word:word.name,inkColor:ink.hex,inkName:ink.name,congruent:word.name===ink.name};
});
