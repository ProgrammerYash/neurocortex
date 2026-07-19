import Btn from './Btn.jsx';

export default function Page({title,onBack,children}) {
  return (
    <div style={{maxWidth:680,margin:"0 auto",padding:"1rem 1rem 4rem"}}>
      <div style={{display:"flex",alignItems:"center",gap:12,padding:"1rem 0 1.5rem"}}>
        <Btn onClick={onBack} style={{padding:"8px 14px",fontSize:13}}>← Back</Btn>
        <h1 style={{margin:0,fontWeight:600,fontSize:18}}>{title}</h1>
      </div>
      {children}
    </div>
  );
}
