import { T } from '../../constants/tokens.js';

export default function MiniBar({label,val,color}) {
  return (
    <div>
      <div style={{display:"flex",justifyContent:"space-between",marginBottom:3}}>
        <span style={{fontSize:10,color:T.muted}}>{label}</span>
        <span style={{fontSize:10,color:T.muted}}>{val}%</span>
      </div>
      <div style={{background:T.faint,borderRadius:4,height:5}}>
        <div style={{background:color,height:5,borderRadius:4,width:`${val}%`,transition:"width .5s ease"}} />
      </div>
    </div>
  );
}
