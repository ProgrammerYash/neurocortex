import { T } from '../../constants/tokens.js';

export default function Btn({children,onClick,primary,style,disabled}) {
  return (
    <button onClick={onClick} disabled={disabled} style={{
      border:primary?"none":`1px solid ${T.faint}`,borderRadius:9,padding:"9px 18px",fontSize:14,cursor:disabled?"not-allowed":"pointer",
      background:primary?`linear-gradient(135deg,${T.tealDim},${T.blueDim})`:"transparent",
      color:primary?"#fff":T.text,fontFamily:T.font,fontWeight:500,opacity:disabled?.5:1,
      transition:"all .18s",...style
    }}>{children}</button>
  );
}
