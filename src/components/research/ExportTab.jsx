import { T } from '../../constants/tokens.js';
import Card from '../ui/Card.jsx';
import Btn from '../ui/Btn.jsx';
import SectionTitle from '../ui/SectionTitle.jsx';

export default function ExportTab({onCSV, onJSON, onXLSX, onParticipantsCSV, sessionCount, participantCount}) {
  return (
    <Card className="fade-in">
      <h3 style={{fontWeight:600,marginBottom:6}}>Export Research Dataset</h3>
      <p style={{color:T.muted,fontSize:13,lineHeight:1.8,marginBottom:20}}>
        All exports are fully anonymized — participant IDs only, no PII.
        Each session row includes all behavioral biomarkers, survey scores, NASA-TLX dimensions, and computed burnout score.
        Compatible with pandas, sklearn, xgboost, lightgbm, catboost, keras.
      </p>

      <SectionTitle>Session Data ({sessionCount} rows)</SectionTitle>
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:10,marginBottom:24}}>
        <Btn onClick={onCSV}  primary style={{padding:"13px",fontSize:13}}>⬇ Sessions CSV</Btn>
        <Btn onClick={onJSON} style={{padding:"13px",fontSize:13,background:"rgba(167,139,250,0.1)",color:T.purple,border:"1px solid rgba(167,139,250,0.2)"}}>⬇ Sessions JSON</Btn>
        <Btn onClick={onXLSX} style={{padding:"13px",fontSize:13,background:"rgba(104,211,145,0.1)",color:T.green,border:"1px solid rgba(104,211,145,0.2)"}}>⬇ Sessions XLSX</Btn>
      </div>

      <SectionTitle>Participant Summary ({participantCount} participants)</SectionTitle>
      <p style={{color:T.muted,fontSize:12,marginBottom:10,lineHeight:1.7}}>
        One row per participant — includes aggregated averages, total sessions, last active date, and latest burnout score.
        Use for participant-level ML features.
      </p>
      <Btn onClick={onParticipantsCSV}
        style={{padding:"13px 24px",fontSize:13,background:"rgba(246,173,85,0.1)",color:T.gold,border:"1px solid rgba(246,173,85,0.2)",marginBottom:24}}>
        ⬇ Download All Participants (CSV)
      </Btn>

      <div style={{background:T.surface,borderRadius:10,padding:"16px"}}>
        <div style={{fontWeight:600,fontSize:13,marginBottom:10,color:T.text}}>Python ML Quick-Start</div>
        <pre style={{fontFamily:T.mono,fontSize:11,color:T.teal,lineHeight:1.9,overflow:"auto",whiteSpace:"pre-wrap"}}>{`import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import shap, lightgbm as lgb

df = pd.read_csv('neurocortex_sessions.csv')
features = [
    'ReactionAvg_ms','TypingWPM','TypingErrorRate',
    'MemoryAccuracy_pct','AttentionAccuracy_pct',
    'Survey_Sleep_hrs','Survey_Stress','Survey_Fatigue',
    'Survey_Motivation','NASATLX_Score'
]
X = df[features].fillna(df[features].mean())
y = (df['BurnoutScore'] > 60).astype(int)  # binary burnout label

model = RandomForestClassifier(n_estimators=200, random_state=42)
model.fit(X, y)
explainer   = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X)
shap.summary_plot(shap_values[1], X, feature_names=features)`}</pre>
      </div>

      <p style={{fontSize:11,color:T.muted,marginTop:12,textAlign:"center"}}>
        {sessionCount} sessions · {participantCount} participants · Research use only · No PII
      </p>
    </Card>
  );
}
