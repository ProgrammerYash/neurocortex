import { T } from '../../constants/tokens.js';
import Card from '../ui/Card.jsx';
import Btn from '../ui/Btn.jsx';
import SectionTitle from '../ui/SectionTitle.jsx';

function formatMetric(value) {
  if (value == null) return '—';
  if (typeof value === 'number') return value.toFixed ? value.toFixed(3) : value;
  return String(value);
}

function formatPercent(value) {
  if (value == null) return '—';
  return `${(Number(value) * 100).toFixed(1)}%`;
}

function getSplitMetrics(model) {
  return model?.metrics?.test ?? model?.metrics?.validation ?? model?.metrics?.train ?? {};
}

function featureLabel(name) {
  const labels = {
    survey_sleep: 'Sleep',
    survey_stress: 'Stress score',
    survey_fatigue: 'Fatigue',
    survey_motivation: 'Motivation',
    reaction_cv: 'Reaction time variability',
    reaction_avg: 'Reaction time',
    typing_irregularity: 'Typing irregularity',
    typing_variance: 'Typing variance',
    memory_efficiency: 'Memory efficiency',
    stroop_interference: 'Stroop interference',
    study_load: 'Study load',
    nasa_tlx_tlxScore: 'NASA-TLX score',
  };
  return labels[name] ?? String(name ?? '').replace(/_/g, ' ');
}

function riskColor(level) {
  if (level === 'high') return T.red;
  if (level === 'medium') return T.orange;
  return T.green;
}

export default function MLTab({
  trainedModels,
  trainingModel,
  onTrainModel,
  latestDatasetId,
  predictions,
  batchPredicting,
  onBatchPredict,
  latestModelId,
  featureImportance,
  modelComparison,
  selectedPrediction,
  selectedExplanation,
  explaining,
  onExplainPrediction,
}) {
  const models = Array.isArray(trainedModels) ? trainedModels : [];
  const rows = Array.isArray(predictions) ? predictions : [];
  const comparison = Array.isArray(modelComparison) ? modelComparison : [];
  const latestModel = models[0] ?? null;
  const metrics = getSplitMetrics(latestModel);
  const ranked = featureImportance?.ranked_features ?? featureImportance?.training_feature_importance ?? [];
  const explanation = selectedExplanation?.explanation ?? null;
  const activePrediction = selectedPrediction ?? rows[0] ?? null;

  return (
    <div className="fade-in" style={{display:"flex",flexDirection:"column",gap:14}}>
      <Card>
        <SectionTitle>ML Training Pipeline</SectionTitle>
        <p style={{color:T.muted,fontSize:13,lineHeight:1.8,marginBottom:14}}>
          Train a LightGBM classifier on labeled dataset rows with participant-level splits.
        </p>
        <Btn
          onClick={onTrainModel}
          disabled={trainingModel || !latestDatasetId}
          style={{
            background:trainingModel ? T.surface : "rgba(45,212,191,0.12)",
            color:trainingModel ? T.muted : T.teal,
            border:"1px solid rgba(45,212,191,0.25)",
            padding:"12px 28px",
            fontSize:14,
            marginBottom:14,
          }}
        >
          {trainingModel
            ? <span><span className="spin" style={{display:"inline-block",marginRight:8}}>⟳</span>Training model…</span>
            : "Train New Model"}
        </Btn>
        <Btn
          onClick={onBatchPredict}
          disabled={batchPredicting || !latestModelId}
          style={{
            background:batchPredicting ? T.surface : "rgba(99,179,237,0.12)",
            color:batchPredicting ? T.muted : T.blue,
            border:"1px solid rgba(99,179,237,0.25)",
            padding:"12px 28px",
            fontSize:14,
          }}
        >
          {batchPredicting ? 'Running batch predictions…' : 'Run Batch Predictions'}
        </Btn>
      </Card>

      <Card>
        <SectionTitle>Model Performance</SectionTitle>
        {latestModel ? (
          <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:10}}>
            <div style={{background:T.surface,borderRadius:8,padding:"12px"}}>
              <div style={{fontSize:11,color:T.muted,marginBottom:4}}>Accuracy</div>
              <div style={{fontSize:22,fontWeight:700}}>{formatPercent(metrics.accuracy)}</div>
            </div>
            <div style={{background:T.surface,borderRadius:8,padding:"12px"}}>
              <div style={{fontSize:11,color:T.muted,marginBottom:4}}>F1 Score</div>
              <div style={{fontSize:22,fontWeight:700}}>{formatMetric(metrics.f1_score)}</div>
            </div>
            <div style={{background:T.surface,borderRadius:8,padding:"12px"}}>
              <div style={{fontSize:11,color:T.muted,marginBottom:4}}>ROC-AUC</div>
              <div style={{fontSize:22,fontWeight:700}}>{formatMetric(metrics.roc_auc)}</div>
            </div>
            <div style={{background:T.surface,borderRadius:8,padding:"12px"}}>
              <div style={{fontSize:11,color:T.muted,marginBottom:4}}>Training Size</div>
              <div style={{fontSize:22,fontWeight:700}}>{latestModel.metrics?.train_rows ?? latestModel.train_size ?? '—'}</div>
            </div>
          </div>
        ) : (
          <div style={{fontSize:12,color:T.muted}}>Train a model to view performance metrics.</div>
        )}
      </Card>

      <Card>
        <SectionTitle>Feature Importance</SectionTitle>
        {ranked.length > 0 ? (
          <div style={{display:"flex",flexDirection:"column",gap:10}}>
            {ranked.slice(0, 10).map((item, index) => (
              <div key={item.feature ?? index} style={{display:"flex",alignItems:"center",gap:12,fontSize:13}}>
                <span style={{minWidth:24,color:T.muted}}>{index + 1}.</span>
                <span style={{flex:1}}>{featureLabel(item.feature)}</span>
                <span style={{color:T.orange,fontWeight:600}}>↑ risk</span>
                <span style={{color:T.muted,minWidth:60,textAlign:"right"}}>{formatMetric(item.score ?? item.importance)}</span>
              </div>
            ))}
          </div>
        ) : (
          <div style={{fontSize:12,color:T.muted}}>Feature importance appears after model training.</div>
        )}
      </Card>

      <Card>
        <SectionTitle>Prediction Explainability</SectionTitle>
        {rows.length > 0 ? (
          <>
            <div style={{display:"flex",gap:8,flexWrap:"wrap",marginBottom:12}}>
              {rows.slice(0, 5).map(row => (
                <button
                  key={row.id}
                  onClick={() => onExplainPrediction?.(row)}
                  style={{
                    padding:"6px 10px",
                    fontSize:11,
                    borderRadius:6,
                    border:`1px solid ${activePrediction?.id === row.id ? T.teal : T.faint}`,
                    background:activePrediction?.id === row.id ? 'rgba(45,212,191,0.12)' : T.surface,
                    color:T.text,
                    cursor:'pointer',
                  }}
                >
                  {row.public_id} · {row.session_date}
                </button>
              ))}
            </div>
            {activePrediction ? (
              <div style={{background:T.surface,borderRadius:8,padding:"14px"}}>
                <div style={{display:"flex",justifyContent:"space-between",marginBottom:10}}>
                  <div>
                    <div style={{fontSize:11,color:T.muted}}>Risk</div>
                    <div style={{fontSize:28,fontWeight:700,color:riskColor(activePrediction.risk_level)}}>
                      {formatPercent(activePrediction.probability)}
                    </div>
                  </div>
                  <Btn
                    onClick={() => onExplainPrediction?.(activePrediction)}
                    disabled={explaining}
                    style={{padding:"8px 14px",fontSize:12}}
                  >
                    {explaining ? 'Explaining…' : 'Generate SHAP Explanation'}
                  </Btn>
                </div>
                {explanation ? (
                  <div style={{display:"flex",flexDirection:"column",gap:8}}>
                    <div style={{fontSize:12,color:T.muted}}>Top contributors</div>
                    {(explanation.contributions ?? [])
                      .filter(item => item.direction === 'increases_risk')
                      .slice(0, 5)
                      .map(item => (
                        <div key={item.feature} style={{fontSize:13,color:T.orange}}>
                          🟠 {featureLabel(item.feature)}
                        </div>
                      ))}
                    {explanation.top_risk_factors?.length > 0 ? (
                      <div style={{fontSize:11,color:T.muted,marginTop:8}}>
                        Top risk factors: {explanation.top_risk_factors.map(featureLabel).join(', ')}
                      </div>
                    ) : null}
                  </div>
                ) : (
                  <div style={{fontSize:12,color:T.muted}}>Select a prediction and generate a SHAP explanation.</div>
                )}
              </div>
            ) : null}
          </>
        ) : (
          <div style={{fontSize:12,color:T.muted}}>Run batch predictions to explain individual risk scores.</div>
        )}
      </Card>

      <Card>
        <SectionTitle>Model Comparison</SectionTitle>
        {comparison.length > 0 ? (
          <div style={{overflowX:"auto"}}>
            <table style={{width:"100%",borderCollapse:"collapse",fontSize:12}}>
              <thead>
                <tr style={{color:T.muted,textAlign:"left"}}>
                  <th style={{padding:"8px 6px"}}>Version</th>
                  <th style={{padding:"8px 6px"}}>Accuracy</th>
                  <th style={{padding:"8px 6px"}}>F1</th>
                  <th style={{padding:"8px 6px"}}>ROC-AUC</th>
                  <th style={{padding:"8px 6px"}}>Created</th>
                </tr>
              </thead>
              <tbody>
                {comparison.map(row => (
                  <tr key={row.model_id} style={{borderTop:`1px solid ${T.faint}`}}>
                    <td style={{padding:"8px 6px"}}>v{row.version}</td>
                    <td style={{padding:"8px 6px"}}>{formatPercent(row.accuracy)}</td>
                    <td style={{padding:"8px 6px"}}>{formatMetric(row.f1)}</td>
                    <td style={{padding:"8px 6px"}}>{formatMetric(row.roc_auc)}</td>
                    <td style={{padding:"8px 6px"}}>{row.created_at ? new Date(row.created_at).toLocaleDateString() : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div style={{fontSize:12,color:T.muted}}>No models available for comparison.</div>
        )}
      </Card>
    </div>
  );
}
