import { T } from '../../constants/tokens.js';

export default function Label({children,style}) {
  return <label style={{fontSize:12,fontWeight:500,color:T.muted,display:"block",marginBottom:6,...style}}>{children}</label>;
}
