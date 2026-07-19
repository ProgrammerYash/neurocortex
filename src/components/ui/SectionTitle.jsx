import { T } from '../../constants/tokens.js';

export default function SectionTitle({children}) {
  return <div style={{fontWeight:600,fontSize:11,marginBottom:12,color:T.muted,textTransform:"uppercase",letterSpacing:1}}>{children}</div>;
}
