import { T } from './tokens.js';

export const css = `
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
*{box-sizing:border-box;margin:0;padding:0}
body{background:${T.bg};color:${T.text};font-family:${T.font};-webkit-font-smoothing:antialiased}
::-webkit-scrollbar{width:4px}::-webkit-scrollbar-track{background:${T.surface}}::-webkit-scrollbar-thumb{background:${T.tealDim};border-radius:4px}
@keyframes fadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.5}}
@keyframes spin{to{transform:rotate(360deg)}}
@keyframes glow{0%,100%{box-shadow:0 0 20px rgba(45,212,191,.15)}50%{box-shadow:0 0 40px rgba(45,212,191,.35)}}
@keyframes heartbeat{0%,100%{transform:scale(1)}50%{transform:scale(1.08)}}
@keyframes slideIn{from{opacity:0;transform:translateX(-12px)}to{opacity:1;transform:translateX(0)}}
.fade-in{animation:fadeIn .35s ease both}
.pulse{animation:pulse 2s infinite}
.spin{animation:spin 1s linear infinite}
.glow{animation:glow 3s ease infinite}
.heartbeat{animation:heartbeat 2s ease infinite}
input,select,textarea{background:${T.surface};border:1px solid ${T.faint};color:${T.text};font-family:${T.font};font-size:14px;border-radius:8px;padding:10px 12px;width:100%;outline:none;transition:border-color .2s}
input:focus,select:focus,textarea:focus{border-color:${T.teal}}
input[type=range]{padding:0;height:6px;accent-color:${T.teal}}
button{font-family:${T.font};cursor:pointer;border:none;outline:none;transition:all .18s}
button:active{transform:scale(.97)}
`;
