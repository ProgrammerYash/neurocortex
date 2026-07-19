import { T } from '../../constants/tokens.js';
import Card from '../ui/Card.jsx';
import SectionTitle from '../ui/SectionTitle.jsx';
import SparkLine from '../ui/SparkLine.jsx';

export default function ResearchOverviewTab({sessions, stats, datasetSummary, datasetQuality}) {
  const safe = Array.isArray(sessions) ? sessions : [];
  const summaryBlock = datasetSummary ? (
    <Card style={{marginBottom:14}}>
      <SectionTitle>Latest Research Dataset</SectionTitle>
      <div style={{display:"grid",gridTemplateColumns:"repeat(3,1fr)",gap:10,fontSize:13,marginBottom:datasetQuality ? 12 : 0}}>
        <div><span style={{color:T.muted}}>Name</span><div style={{fontWeight:600}}>{datasetSummary.name}</div></div>
        <div><span style={{color:T.muted}}>Schema</span><div style={{fontWeight:600}}>{datasetSummary.feature_schema_version}</div></div>
        <div><span style={{color:T.muted}}>Rows</span><div style={{fontWeight:600}}>{datasetSummary.row_count}</div></div>
        <div><span style={{color:T.muted}}>Participants</span><div style={{fontWeight:600}}>{datasetSummary.participant_count}</div></div>
        <div><span style={{color:T.muted}}>Valid for ML</span><div style={{fontWeight:600}}>{datasetSummary.valid_for_ml_count}</div></div>
        <div><span style={{color:T.muted}}>Complete Days</span><div style={{fontWeight:600}}>{datasetSummary.complete_day_count}</div></div>
      </div>
      {datasetQuality ? (
        <div style={{display:"grid",gridTemplateColumns:"repeat(5,1fr)",gap:10,fontSize:13,borderTop:`1px solid ${T.cardBorder}`,paddingTop:12}}>
          <div><span style={{color:T.muted}}>Training Rows</span><div style={{fontWeight:600}}>{datasetQuality.valid_training_rows ?? "—"}</div></div>
          <div><span style={{color:T.muted}}>Burnout Prev.</span><div style={{fontWeight:600}}>{datasetQuality.burnout_prevalence_percent != null ? `${datasetQuality.burnout_prevalence_percent}%` : "—"}</div></div>
          <div><span style={{color:T.muted}}>Dropout Prev.</span><div style={{fontWeight:600}}>{datasetQuality.dropout_prevalence_percent != null ? `${datasetQuality.dropout_prevalence_percent}%` : "—"}</div></div>
          <div><span style={{color:T.muted}}>Avg Completion</span><div style={{fontWeight:600}}>{datasetQuality.average_completion_rate != null ? `${datasetQuality.average_completion_rate}%` : "—"}</div></div>
          <div><span style={{color:T.muted}}>Quality Score</span><div style={{fontWeight:600}}>{datasetQuality.quality_score ?? "—"}</div></div>
        </div>
      ) : null}
    </Card>
  ) : null;

  if (safe.length === 0) return (
    <div className="fade-in" style={{display:"flex",flexDirection:"column",gap:14}}>
      {summaryBlock}
      <Card>
        <div style={{textAlign:"center",padding:"3rem"}}>
          <div style={{fontSize:40,marginBottom:12}}>📭</div>
          <div style={{fontWeight:600,fontSize:16,marginBottom:8}}>No session data yet</div>
          <p style={{color:T.muted,fontSize:13,lineHeight:1.7}}>
            Once participants complete sessions, study trends will appear here.<br/>
            Register participants and have them complete the daily protocol.
          </p>
        </div>
      </Card>
    </div>
  );

  // Build a 30-day rolling count — guarded against bad date strings
  const dailyCounts = Array.from({length:30},(_,i)=>{
    const d = new Date(); d.setDate(d.getDate()-29+i);
    const ds = d.toISOString().split("T")[0];
    return safe.filter(s => s?.date === ds).length;
  });

  const last30 = safe.slice(-30);

  return (
    <div className="fade-in" style={{display:"flex",flexDirection:"column",gap:14}}>
      {summaryBlock}
      <Card>
        <SectionTitle>Daily Session Volume — Last 30 Days</SectionTitle>
        {/* CRASH-8 fix: pass explicit numeric max so SparkLine never gets null */}
        <SparkLine data={dailyCounts} color={T.teal} max={Math.max(1,...dailyCounts)} />
      </Card>
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:14}}>
        <Card>
          <SectionTitle>Reaction Time Trend (ms)</SectionTitle>
          <SparkLine data={last30.map(s=>s?.reaction?.avg ?? null)} color={T.blue} max={0}/>
        </Card>
        <Card>
          <SectionTitle>Stress Trend (1-10)</SectionTitle>
          <SparkLine data={last30.map(s=>s?.survey?.stress ?? null)} color={T.red} max={10}/>
        </Card>
        <Card>
          <SectionTitle>Memory Accuracy Trend (%)</SectionTitle>
          <SparkLine data={last30.map(s=>s?.memory?.accuracy ?? null)} color={T.purple} max={100}/>
        </Card>
        <Card>
          <SectionTitle>Average Sleep (hrs)</SectionTitle>
          <SparkLine data={last30.map(s=>s?.survey?.sleep ?? null)} color={T.green} max={12}/>
        </Card>
      </div>
    </div>
  );
}
