import { useEffect, useRef } from 'react';

export function useInterval(cb, ms, active=true) {
  const ref=useRef(cb);
  useEffect(()=>{ref.current=cb},[cb]);
  useEffect(()=>{if(!active)return;const id=setInterval(()=>ref.current(),ms);return()=>clearInterval(id);},[ms,active]);
}
