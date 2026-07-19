import { T } from '../../constants/tokens.js';

export default function Toast({msg,type}) {
  const colors={info:T.blue,success:T.green,error:T.red};
  return (
    <div style={{position:"fixed",bottom:80,left:"50%",transform:"translateX(-50%)",background:T.card,border:`1px solid ${colors[type]||T.teal}40`,borderRadius:10,padding:"12px 20px",fontSize:14,color:T.text,zIndex:9999,animation:"fadeIn .3s ease",boxShadow:`0 4px 24px rgba(0,0,0,0.4)`,maxWidth:340,textAlign:"center"}}>
      {msg}
    </div>
  );
}
