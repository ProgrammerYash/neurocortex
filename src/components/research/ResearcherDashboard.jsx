import { useState, useEffect, useMemo } from 'react';
import { T } from '../../constants/tokens.js';
import Store from '../../store/index.js';
import {
  fetchResearchDatasetQuality,
  fetchResearchDatasetSummary,
  fetchResearchDatasets,
  batchPredict,
  compareModels,
  explainPrediction,
  fetchResearchModels,
  fetchStudyConfig,
  getExplanation,
  getFeatureImportance,
  getPredictions,
  labelResearchDataset,
  trainResearchModel,
} from '../../store/research.js';
import { dateToday } from '../../utils/dates.js';
import { calcBurnout } from '../../utils/burnout.js';
import { buildXLSX, safeDownload } from '../../utils/export.js';
import Btn from '../ui/Btn.jsx';
import Card from '../ui/Card.jsx';
import StudyBanner from '../ui/StudyBanner.jsx';
import ResearchOverviewTab from './ResearchOverviewTab.jsx';
import ParticipantsTab from './ParticipantsTab.jsx';
import MLTab from './MLTab.jsx';
import HumanParticipantsTab from './HumanParticipantsTab.jsx';
import DataQualityTab from './DataQualityTab.jsx';
import ExportTab from './ExportTab.jsx';
import ConsentFormsTab from './ConsentFormsTab.jsx';

export default function ResearcherDashboard({onBack}) {
  const [allSessions,    setAllSessions]    = useState([]);
  const [allParticipants,setAllParticipants]= useState([]);
  const [tab,            setTab]            = useState("overview");
  const [filters,        setFilters]        = useState({dateFrom:"",dateTo:""});
  const [loadError,      setLoadError]      = useState(null);
  const [datasetSummary, setDatasetSummary]  = useState(null);
  const [datasetQuality,   setDatasetQuality]   = useState(null);
  const [trainedModels,    setTrainedModels]    = useState([]);
  const [latestDatasetId,  setLatestDatasetId]  = useState(null);
  const [trainingModel,    setTrainingModel]    = useState(false);
  const [predictions,      setPredictions]      = useState([]);
  const [batchPredicting,  setBatchPredicting]  = useState(false);
  const [featureImportance,setFeatureImportance]= useState(null);
  const [modelComparison,  setModelComparison]  = useState([]);
  const [selectedPrediction,setSelectedPrediction]= useState(null);
  const [selectedExplanation,setSelectedExplanation]= useState(null);
  const [explaining,       setExplaining]       = useState(false);
  const [studyConfig,      setStudyConfig]      = useState(null);

  // CRASH-1/2 fix: all loading in try/catch; never crashes on bad data
  useEffect(()=>{
    let cancelled = false;
    (async ()=>{
      try {
        const [sessions, participants, datasets, models, predictionRows, comparisonRows, config] = await Promise.all([
          Store.getAllSessions(),
          Store.getAllParticipants(),
          fetchResearchDatasets().catch(() => []),
          fetchResearchModels().catch(() => []),
          getPredictions().catch(() => []),
          compareModels().catch(() => []),
          fetchStudyConfig().catch(() => null),
        ]);
        if (cancelled) return;
        setStudyConfig(config);
        setAllSessions(Array.isArray(sessions) ? sessions : []);
        setAllParticipants(Array.isArray(participants) ? participants : []);
        setTrainedModels(Array.isArray(models) ? models : []);
        setPredictions(Array.isArray(predictionRows) ? predictionRows : []);
        setModelComparison(Array.isArray(comparisonRows) ? comparisonRows : []);
        if (Array.isArray(models) && models.length > 0) {
          const importance = await getFeatureImportance(models[0].id).catch(() => null);
          if (!cancelled) setFeatureImportance(importance);
        } else {
          setFeatureImportance(null);
        }
        if (Array.isArray(datasets) && datasets.length > 0) {
          const latest = datasets[0];
          setLatestDatasetId(latest.id);
          const [summary, quality] = await Promise.all([
            fetchResearchDatasetSummary(latest.id),
            fetchResearchDatasetQuality(latest.id).catch(() => null),
          ]);
          if (!cancelled) {
            setDatasetSummary(summary);
            setDatasetQuality(quality);
          }
        } else {
          setDatasetSummary(null);
          setDatasetQuality(null);
          setLatestDatasetId(null);
        }
      } catch(e) {
        if (cancelled) return;
        console.error("ResearcherDashboard load error:", e);
        setLoadError(e.message ?? "Unknown load error");
        setAllSessions([]); setAllParticipants([]);
        setDatasetSummary(null);
        setDatasetQuality(null);
        setLatestDatasetId(null);
        setTrainedModels([]);
        setPredictions([]);
        setModelComparison([]);
        setFeatureImportance(null);
        setStudyConfig(null);
      }
    })();
    return () => { cancelled = true; };
  },[]);

  // Participants = all non-researcher profiles; null-safe filter
  const participants = useMemo(()=>
    (allParticipants||[]).filter(p => p?.id && p?.role !== "researcher")
  ,[allParticipants]);

  // Sessions filtered by date range only; every item null-checked
  const filtered = useMemo(()=>{
    let s = (allSessions||[]).filter(s => s && typeof s==="object" && s.participantID && s.date);
    if (filters.dateFrom) s = s.filter(s => s.date >= filters.dateFrom);
    if (filters.dateTo)   s = s.filter(s => s.date <= filters.dateTo);
    return s;
  },[allSessions, filters]);

  // Study overview stats — fully null-guarded, returns zeroes on error
  const stats = useMemo(()=>{
    try {
      const withR  = filtered.filter(s => s?.reaction?.avg > 0);
      const withS  = filtered.filter(s => s?.survey);
      const withM  = filtered.filter(s => typeof s?.memory?.accuracy === "number");
      const withA  = filtered.filter(s => typeof s?.attention?.accuracy === "number");
      const complete = filtered.filter(s => s?.reaction&&s?.typing&&s?.memory&&s?.attention&&s?.survey);
      const recentIds = new Set(
        filtered.filter(s => {
          try { return (Date.now()-new Date(s.date).getTime())/86400000 <= 7; }
          catch { return false; }
        }).map(s => s.participantID)
      );
      const safeAvg = (arr, fn) =>
        arr.length > 0 ? arr.reduce((a,s)=>a+(Number(fn(s))||0), 0)/arr.length : 0;
      return {
        total:        participants.length,
        sessions:     filtered.length,
        active:       recentIds.size,
        completion:   filtered.length>0 ? Math.round(complete.length/filtered.length*100) : 0,
        avgReaction:  Math.round(safeAvg(withR, s=>s.reaction?.avg)),
        avgStress:    +safeAvg(withS, s=>s.survey?.stress).toFixed(1),
        avgFatigue:   +safeAvg(withS, s=>s.survey?.fatigue).toFixed(1),
        avgSleep:     +safeAvg(withS, s=>s.survey?.sleep).toFixed(1),
        avgMemory:    Math.round(safeAvg(withM, s=>s.memory?.accuracy)),
        avgAttention: Math.round(safeAvg(withA, s=>s.attention?.accuracy)),
      };
    } catch(e) {
      console.error("stats calc error:", e);
      return {total:0,sessions:0,active:0,completion:0,avgReaction:0,avgStress:0,avgFatigue:0,avgSleep:0,avgMemory:0,avgAttention:0};
    }
  },[filtered, participants]);

  // ── CSV EXPORT (sessions) ────────────────────────────────────────
  // CRASH-6 fix: wrapped in try/catch; URL revoked after download
  const exportCSV = () => {
    try {
      const headers = [
        "ParticipantID","Date","Grade","AgeRange","SessionComplete",
        "ReactionAvg_ms","ReactionMedian_ms","ReactionSD_ms","ReactionMin_ms","ReactionMax_ms","ReactionMissed",
        "TypingWPM","TypingErrorRate","TypingBackspaces","TypingAvgInterval_ms","TypingVariance","TypingDwellTime_ms","TypingPauseFreq",
        "MemoryAccuracy_pct","MemoryResponseTime_ms","MemoryCorrect","MemoryTotal",
        "AttentionAccuracy_pct","AttentionAvgRT_ms","AttentionErrors","AttentionInterference",
        "Survey_Sleep_hrs","Survey_Study_hrs","Survey_Homework_hrs","Survey_ScreenTime_hrs","Survey_Exercise_min","Survey_Water_cups",
        "Survey_Stress","Survey_Fatigue","Survey_Motivation","Survey_Mood","Survey_SocialStress","Survey_ExamPressure",
        "NASATLX_Score","NASATLX_Mental","NASATLX_Physical","NASATLX_Temporal","NASATLX_Performance","NASATLX_Effort","NASATLX_Frustration",
        "BurnoutScore"
      ];
      const rows = filtered.map(s => [
        s.participantID ?? "",
        s.date ?? "",
        s.grade ?? "",
        s.ageRange ?? "",
        s.complete ? 1 : 0,
        s.reaction?.avg        ?? "", s.reaction?.median    ?? "", s.reaction?.sd      ?? "",
        s.reaction?.min        ?? "", s.reaction?.max       ?? "", s.reaction?.missed  ?? "",
        s.typing?.wpm          ?? "", s.typing?.errorRate   ?? "", s.typing?.backspaces ?? "",
        s.typing?.avgInterval  ?? "", s.typing?.variance    ?? "", s.typing?.avgDwell  ?? "",
        s.typing?.pauseFrequency ?? "",
        s.memory?.accuracy     ?? "", s.memory?.responseTime ?? "", s.memory?.correct  ?? "", s.memory?.total ?? "",
        s.attention?.accuracy  ?? "", s.attention?.avgRT    ?? "", s.attention?.errors ?? "",
        s.attention?.interferenceScore ?? "",
        s.survey?.sleep        ?? "", s.survey?.study       ?? "", s.survey?.homework  ?? "",
        s.survey?.screenTime   ?? "", s.survey?.exercise    ?? "", s.survey?.water     ?? "",
        s.survey?.stress       ?? "", s.survey?.fatigue     ?? "", s.survey?.motivation ?? "",
        s.survey?.mood         ?? "", s.survey?.socialStress ?? "",
        s.survey?.exam ? 1 : (s.survey ? 0 : ""),
        s.nasaTLX?.tlxScore    ?? "", s.nasaTLX?.mentalDemand  ?? "", s.nasaTLX?.physicalDemand ?? "",
        s.nasaTLX?.temporalDemand ?? "", s.nasaTLX?.performance ?? "", s.nasaTLX?.effort ?? "",
        s.nasaTLX?.frustration ?? "",
        calcBurnout(s) ?? "",
      ]);
      const csv = [headers, ...rows].map(r => r.map(v=>String(v).includes(",") ? `"${v}"` : v).join(",")).join("\n");
      safeDownload(csv, `neurocortex_sessions_${dateToday()}.csv`, "text/csv");
    } catch(e) { alert("CSV export error: "+e.message); }
  };

  // ── PARTICIPANTS CSV (one row per participant) ────────────────────
  const exportParticipantsCSV = () => {
    try {
      const headers = [
        "ParticipantID","Grade","AgeRange","JoinedDate",
        "TotalSessions","CompleteSessions","LastActiveDate",
        "AvgReaction_ms","AvgStress","AvgFatigue","AvgSleep",
        "AvgMemory_pct","AvgAttention_pct","LatestBurnoutScore","StudyDays"
      ];
      const rows = participants.map(p => {
        const pSess = filtered.filter(s => s.participantID === p.id);
        const complete = pSess.filter(s=>s.complete).length;
        const lastDate = pSess.length>0 ? (pSess[pSess.length-1]?.date ?? "—") : "—";
        const safeAvg = (arr,fn) => arr.length>0 ? +(arr.reduce((a,s)=>a+(Number(fn(s))||0),0)/arr.length).toFixed(1) : "";
        const withR = pSess.filter(s=>s?.reaction?.avg>0);
        const withS = pSess.filter(s=>s?.survey);
        const withM = pSess.filter(s=>typeof s?.memory?.accuracy==="number");
        const withA = pSess.filter(s=>typeof s?.attention?.accuracy==="number");
        const latestSurvey = pSess.filter(s=>s.survey).slice(-1)[0];
        return [
          p.id ?? "",
          p.grade ?? "",
          p.ageRange ?? "",
          p.joinedDate ?? "",
          pSess.length,
          complete,
          lastDate,
          safeAvg(withR, s=>s.reaction?.avg),
          safeAvg(withS, s=>s.survey?.stress),
          safeAvg(withS, s=>s.survey?.fatigue),
          safeAvg(withS, s=>s.survey?.sleep),
          safeAvg(withM, s=>s.memory?.accuracy),
          safeAvg(withA, s=>s.attention?.accuracy),
          calcBurnout(latestSurvey) ?? "",
          pSess.filter(s=>s.complete).length,
        ];
      });
      const csv = [headers, ...rows].map(r => r.join(",")).join("\n");
      safeDownload(csv, `neurocortex_participants_${dateToday()}.csv`, "text/csv");
    } catch(e) { alert("Participants CSV error: "+e.message); }
  };

  // ── JSON EXPORT ──────────────────────────────────────────────────
  const exportJSON = () => {
    try {
      const payload = {
        metadata: {
          exportDate: new Date().toISOString(),
          platform: "NeuroCortex v3",
          totalParticipants: participants.length,
          totalSessions: filtered.length,
          dateRange: filters,
        },
        participants: participants.map(p => ({
          id:         p.id,
          grade:      p.grade      ?? null,
          ageRange:   p.ageRange   ?? null,
          joinedDate: p.joinedDate ?? null,
        })),
        sessions: filtered,
      };
      safeDownload(JSON.stringify(payload, null, 2), `neurocortex_dataset_${dateToday()}.json`, "application/json");
    } catch(e) { alert("JSON export error: "+e.message); }
  };

  // ── XLSX EXPORT ──────────────────────────────────────────────────
  const exportXLSX = () => {
    try {
      const headers = [
        "ParticipantID","Date","Grade","AgeRange","Complete",
        "ReactionAvg_ms","TypingWPM","TypingErrorRate","MemoryAccuracy_pct",
        "AttentionAccuracy_pct","Sleep_hrs","Stress","Fatigue","Motivation",
        "NASATLX_Score","BurnoutScore"
      ];
      const rows = filtered.map(s => [
        s.participantID ?? "", s.date ?? "", s.grade ?? "", s.ageRange ?? "",
        s.complete ? 1 : 0,
        s.reaction?.avg ?? "", s.typing?.wpm ?? "", s.typing?.errorRate ?? "",
        s.memory?.accuracy ?? "", s.attention?.accuracy ?? "",
        s.survey?.sleep ?? "", s.survey?.stress ?? "", s.survey?.fatigue ?? "",
        s.survey?.motivation ?? "", s.nasaTLX?.tlxScore ?? "",
        calcBurnout(s) ?? "",
      ]);
      safeDownload(buildXLSX(headers, rows), `neurocortex_dataset_${dateToday()}.xls`, "application/vnd.ms-excel");
    } catch(e) { alert("XLSX export error: "+e.message); }
  };

  // ── ML pipeline ──────────────────────────────────────────────────
  const latestModelId = trainedModels[0]?.id ?? null;

  const refreshModelInsights = async (modelId) => {
    if (!modelId) {
      setFeatureImportance(null);
      setModelComparison([]);
      return;
    }
    const [importance, comparisonRows] = await Promise.all([
      getFeatureImportance(modelId).catch(() => null),
      compareModels().catch(() => []),
    ]);
    setFeatureImportance(importance);
    setModelComparison(Array.isArray(comparisonRows) ? comparisonRows : []);
  };

  const handleBatchPredict = async () => {
    if (!latestModelId || batchPredicting) return;
    setBatchPredicting(true);
    try {
      await batchPredict(latestModelId);
      const rows = await getPredictions();
      setPredictions(Array.isArray(rows) ? rows : []);
      if (rows?.length > 0) setSelectedPrediction(rows[0]);
      await refreshModelInsights(latestModelId);
    } catch (e) {
      alert(`Batch prediction failed: ${e.message ?? 'Unknown error'}`);
    } finally {
      setBatchPredicting(false);
    }
  };

  const handleExplainPrediction = async (prediction) => {
    if (!prediction?.id || explaining) return;
    setSelectedPrediction(prediction);
    setExplaining(true);
    try {
      let result = await getExplanation(prediction.id).catch(() => null);
      if (!result) result = await explainPrediction(prediction.id);
      setSelectedExplanation(result);
      if (latestModelId) await refreshModelInsights(latestModelId);
    } catch (e) {
      alert(`Explanation failed: ${e.message ?? 'Unknown error'}`);
    } finally {
      setExplaining(false);
    }
  };

  const handleTrainModel = async () => {
    if (!latestDatasetId || trainingModel) return;
    setTrainingModel(true);
    try {
      await labelResearchDataset(latestDatasetId).catch(() => null);
      await trainResearchModel({ datasetId: latestDatasetId });
      const models = await fetchResearchModels();
      setTrainedModels(Array.isArray(models) ? models : []);
      if (models?.length > 0) await refreshModelInsights(models[0].id);
    } catch (e) {
      alert(`Model training failed: ${e.message ?? 'Unknown error'}`);
    } finally {
      setTrainingModel(false);
    }
  };

  // ── If the Store load itself threw, show a non-crashing error UI ─
  if (loadError) {
    return (
      <div style={{maxWidth:900,margin:"0 auto",padding:"2rem"}}>
        <Card>
          <div style={{color:T.red,fontWeight:600,marginBottom:8}}>⚠️ Data Load Error</div>
          <p style={{color:T.muted,fontSize:13,marginBottom:16}}>{loadError}</p>
          <p style={{color:T.muted,fontSize:12}}>This usually means localStorage contains corrupted data. Clear site data and try again, or contact the study coordinator.</p>
          <Btn onClick={onBack} style={{marginTop:16}}>← Sign Out</Btn>
        </Card>
      </div>
    );
  }

  return (
    <div style={{maxWidth:960,margin:"0 auto",padding:"1rem 1rem 3rem"}}>
      {/* Header */}
      <div style={{display:"flex",alignItems:"center",gap:12,padding:"1rem 0 1.5rem",flexWrap:"wrap"}}>
        <Btn onClick={onBack} style={{padding:"8px 14px",fontSize:13}}>← Sign Out</Btn>
        <h1 style={{fontWeight:700,fontSize:20,margin:0}}>Research Dashboard</h1>
        <span style={{fontSize:11,background:`rgba(167,139,250,0.15)`,color:T.purple,padding:"3px 10px",borderRadius:20,border:`1px solid rgba(167,139,250,0.3)`}}>RESEARCHER</span>
        <span style={{marginLeft:"auto",fontSize:11,color:T.muted}}>{participants.length} participants · {filtered.length} sessions</span>
      </div>

      {studyConfig?.show_experimental_banner ? (
        <StudyBanner
          title="Experimental Research Model"
          message="Not validated for clinical or diagnostic use."
        />
      ) : null}

      {/* Study Overview — 6 stat cards */}
      <div style={{display:"grid",gridTemplateColumns:"repeat(3,1fr)",gap:10,marginBottom:10}}>
        {[
          {l:"Total Participants",  v: stats.total,                                    c:T.teal,   icon:"👥"},
          {l:"Total Sessions",      v: stats.sessions,                                 c:T.blue,   icon:"📅"},
          {l:"Active (Last 7d)",    v: stats.active,                                   c:T.green,  icon:"✅"},
          {l:"Avg Reaction Time",   v: stats.avgReaction  ? stats.avgReaction+"ms":"—",c:T.purple, icon:"⚡"},
          {l:"Avg Stress (1-10)",   v: stats.avgStress    ? stats.avgStress           :"—",c:T.red,    icon:"😓"},
          {l:"Avg Fatigue (1-10)",  v: stats.avgFatigue   ? stats.avgFatigue          :"—",c:T.orange, icon:"😴"},
          {l:"Avg Sleep (hrs)",     v: stats.avgSleep     ? stats.avgSleep            :"—",c:T.blue,   icon:"🌙"},
          {l:"Avg Memory Acc.",     v: stats.avgMemory    ? stats.avgMemory+"%"       :"—",c:T.teal,   icon:"🧩"},
          {l:"Session Completion",  v: stats.completion   ? stats.completion+"%"      :"—",c:T.gold,   icon:"🏆"},
        ].map(({l,v,c,icon})=>(
          <div key={l} style={{background:T.card,border:`1px solid ${T.cardBorder}`,borderRadius:12,padding:"14px 16px",display:"flex",alignItems:"center",gap:12}}>
            <span style={{fontSize:22}}>{icon}</span>
            <div>
              <div style={{fontSize:10,color:T.muted,marginBottom:2}}>{l}</div>
              <div style={{fontSize:20,fontWeight:700,color:c}}>{v ?? "—"}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Date range filter */}
      <Card style={{marginBottom:16}}>
        <div style={{display:"flex",alignItems:"center",gap:16,flexWrap:"wrap"}}>
          <span style={{fontSize:12,color:T.muted,fontWeight:500}}>Date filter:</span>
          <div style={{display:"flex",alignItems:"center",gap:8}}>
            <label style={{fontSize:11,color:T.muted}}>From</label>
            <input type="date" value={filters.dateFrom}
              onChange={e=>setFilters(f=>({...f,dateFrom:e.target.value}))}
              style={{width:"auto",padding:"6px 10px",fontSize:12}} />
          </div>
          <div style={{display:"flex",alignItems:"center",gap:8}}>
            <label style={{fontSize:11,color:T.muted}}>To</label>
            <input type="date" value={filters.dateTo}
              onChange={e=>setFilters(f=>({...f,dateTo:e.target.value}))}
              style={{width:"auto",padding:"6px 10px",fontSize:12}} />
          </div>
          {(filters.dateFrom||filters.dateTo)&&(
            <button onClick={()=>setFilters({dateFrom:"",dateTo:""})}
              style={{fontSize:11,color:T.muted,background:"none",border:`1px solid ${T.faint}`,borderRadius:6,padding:"5px 10px",cursor:"pointer"}}>
              Clear
            </button>
          )}
        </div>
      </Card>

      {/* Tabs */}
      <div style={{display:"flex",gap:4,background:T.surface,padding:4,borderRadius:10,marginBottom:18}}>
        {[["overview","📊 Overview"],["participants","👥 Participants"],["quality","🧪 Data Quality"],["ml","🤖 ML / SHAP"],["human","📄 Human Participants"],["consents","✍ Consent Forms"],["export","⬇ Export"]].map(([k,l])=>(
          <button key={k} onClick={()=>setTab(k)}
            style={{flex:1,padding:"9px",border:"none",borderRadius:7,fontWeight:500,fontSize:13,cursor:"pointer",
                    background:tab===k?T.card:T.surface,color:tab===k?T.teal:T.muted,transition:"all .2s"}}>
            {l}
          </button>
        ))}
      </div>

      {tab==="overview"     && <ResearchOverviewTab sessions={filtered} stats={stats} datasetSummary={datasetSummary} datasetQuality={datasetQuality} />}
      {tab==="participants" && <ParticipantsTab participants={participants} allSessions={allSessions} filteredSessions={filtered} />}
      {tab==="quality"      && <DataQualityTab />}
      {tab==="ml"           && <MLTab trainedModels={trainedModels} trainingModel={trainingModel} onTrainModel={handleTrainModel} latestDatasetId={latestDatasetId} predictions={predictions} batchPredicting={batchPredicting} onBatchPredict={handleBatchPredict} latestModelId={latestModelId} featureImportance={featureImportance} modelComparison={modelComparison} selectedPrediction={selectedPrediction} selectedExplanation={selectedExplanation} explaining={explaining} onExplainPrediction={handleExplainPrediction} />}
      {tab==="human"        && <HumanParticipantsTab />}
      {tab==="consents"     && <ConsentFormsTab />}
      {tab==="export"       && <ExportTab
          onCSV={exportCSV} onJSON={exportJSON} onXLSX={exportXLSX}
          onParticipantsCSV={exportParticipantsCSV}
          sessionCount={filtered.length} participantCount={participants.length} />}
    </div>
  );
}
