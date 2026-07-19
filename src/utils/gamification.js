export const calcLevel = (xp) => Math.floor(Math.sqrt(xp/50))+1;
export const evolStage = (lvl) => lvl>=30?"legendary":lvl>=20?"adult":lvl>=10?"teen":lvl>=5?"young":"baby";
export const evolEmoji = (stage) => ({baby:"🥚",young:"🌱",teen:"⚡",adult:"🌟",legendary:"👑"}[stage]);
