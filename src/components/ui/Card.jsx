import { T } from '../../constants/tokens.js';

export default function Card({children,style,className}) {
  return <div className={className} style={{background:T.card,border:`1px solid ${T.cardBorder}`,borderRadius:14,padding:"18px 20px",...style}}>{children}</div>;
}
