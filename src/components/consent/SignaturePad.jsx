import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react';
import { T } from '../../constants/tokens.js';
import Btn from '../ui/Btn.jsx';

const SignaturePad = forwardRef(function SignaturePad({ label, onChange }, ref) {
  const canvasRef = useRef(null);
  const drawingRef = useRef(false);
  const pointsRef = useRef([]);
  const [blank, setBlank] = useState(true);

  const draw = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const scaleX = canvas.width / Math.max(canvas.clientWidth, 1);
    const scaleY = canvas.height / Math.max(canvas.clientHeight, 1);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = '#111827';
    ctx.lineWidth = Math.max(2, 2 * scaleX);
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    for (const stroke of pointsRef.current) {
      if (stroke.length < 2) continue;
      ctx.beginPath();
      ctx.moveTo(stroke[0].x * scaleX, stroke[0].y * scaleY);
      stroke.slice(1).forEach(point => ctx.lineTo(point.x * scaleX, point.y * scaleY));
      ctx.stroke();
    }
  };

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return undefined;
    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      const ratio = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.round(rect.width * ratio);
      canvas.height = Math.round(rect.height * ratio);
      draw();
    };
    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(canvas);
    return () => observer.disconnect();
  }, []);

  const updateBlank = () => {
    const nextBlank = pointsRef.current.every(stroke => stroke.length < 2);
    setBlank(nextBlank);
    onChange?.(!nextBlank);
  };

  const pointFor = event => {
    const rect = canvasRef.current.getBoundingClientRect();
    return {
      x: Math.max(0, Math.min(rect.width, event.clientX - rect.left)),
      y: Math.max(0, Math.min(rect.height, event.clientY - rect.top)),
    };
  };

  const start = event => {
    event.preventDefault();
    canvasRef.current.setPointerCapture(event.pointerId);
    drawingRef.current = true;
    pointsRef.current.push([pointFor(event)]);
  };
  const move = event => {
    if (!drawingRef.current) return;
    event.preventDefault();
    pointsRef.current.at(-1).push(pointFor(event));
    draw();
    updateBlank();
  };
  const stop = event => {
    if (!drawingRef.current) return;
    drawingRef.current = false;
    if (canvasRef.current.hasPointerCapture(event.pointerId)) {
      canvasRef.current.releasePointerCapture(event.pointerId);
    }
    updateBlank();
  };
  const clear = () => {
    pointsRef.current = [];
    draw();
    updateBlank();
  };

  useImperativeHandle(ref, () => ({
    clear,
    isBlank: () => pointsRef.current.every(stroke => stroke.length < 2),
    toPNG: () => {
      if (pointsRef.current.every(stroke => stroke.length < 2)) return null;
      return canvasRef.current.toDataURL('image/png');
    },
  }), []);

  return (
    <div>
      <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:8}}>
        <label style={{fontSize:13, fontWeight:600}}>{label}</label>
        <Btn onClick={clear} disabled={blank} style={{fontSize:12, padding:'5px 10px'}}>Clear</Btn>
      </div>
      <canvas
        ref={canvasRef}
        aria-label={label}
        role="img"
        tabIndex={0}
        onPointerDown={start}
        onPointerMove={move}
        onPointerUp={stop}
        onPointerCancel={stop}
        onContextMenu={event => event.preventDefault()}
        onDrop={event => event.preventDefault()}
        onPaste={event => event.preventDefault()}
        style={{display:'block', width:'100%', height:180, maxHeight:220, border:`1px solid ${T.faint}`, borderRadius:8, background:'#fff', touchAction:'none'}}
      />
      <p style={{fontSize:11, color:T.muted, lineHeight:1.5, marginTop:6}}>
        Sign in the box with a mouse, finger, or stylus. Keyboard users: use a supported pointer device or ask for assistance; pasted or uploaded signatures are not accepted.
      </p>
    </div>
  );
});

export default SignaturePad;
