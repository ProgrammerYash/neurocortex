import Page from './Page.jsx';
import Card from './Card.jsx';
import { T } from '../../constants/tokens.js';

export default function LockedScreen({onBack}) {
  return (
    <Page title="Module Locked" onBack={onBack}>
      <Card style={{textAlign:"center",padding:"3rem"}}>
        <div style={{fontSize:48,marginBottom:16}}>🔒</div>
        <h2 style={{fontWeight:600,marginBottom:8,color:T.teal}}>Already Completed Today</h2>
        <p style={{color:T.muted,fontSize:14,lineHeight:1.8}}>You've already completed this module today.<br/>Come back tomorrow to continue the study.</p>
      </Card>
    </Page>
  );
}
