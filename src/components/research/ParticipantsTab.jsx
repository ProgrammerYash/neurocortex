import { T } from '../../constants/tokens.js';
import { calcBurnout } from '../../utils/burnout.js';
import Card from '../ui/Card.jsx';
import SectionTitle from '../ui/SectionTitle.jsx';

export default function ParticipantsTab({participants, allSessions, filteredSessions}) {
  const safeParts = Array.isArray(participants) ? participants : [];
  const safeSess  = Array.isArray(allSessions)  ? allSessions  : [];

  if (safeParts.length === 0) return (
    <Card className="fade-in">
      <div style={{textAlign:"center",padding:"3rem"}}>
        <div style={{fontSize:40,marginBottom:12}}>👤</div>
        <div style={{fontWeight:600,fontSize:16,marginBottom:8}}>No participants yet</div>
        <p style={{color:T.muted,fontSize:13}}>Participants appear here once they register.</p>
      </div>
    </Card>
  );

  return (
    <div className="fade-in">
      <Card>
        <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",marginBottom:16}}>
          <SectionTitle>Participant Roster — {safeParts.length} enrolled</SectionTitle>
        </div>
        <div style={{overflowX:"auto"}}>
          <table style={{width:"100%",fontSize:12,borderCollapse:"collapse",minWidth:700}}>
            <thead>
              <tr style={{borderBottom:`1px solid ${T.faint}`}}>
                {["Participant ID","Grade","Age Range","Joined","Sessions","Last Active","Status","Burnout Score"].map(h=>(
                  <th key={h} style={{padding:"8px 12px",textAlign:"left",color:T.muted,fontWeight:600,fontSize:11,whiteSpace:"nowrap"}}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {safeParts.map(p => {
                // CRASH-4: every access null-guarded
                if (!p?.id) return null;
                const pSessions = safeSess.filter(s => s?.participantID === p.id);
                const lastDate  = pSessions.length > 0
                  ? (pSessions[pSessions.length-1]?.date ?? "—")
                  : "—";
                // CRASH-4: date arithmetic wrapped in try/catch
                let isActive = false;
                try {
                  isActive = lastDate !== "—" &&
                    (Date.now() - new Date(lastDate).getTime()) / 86400000 <= 7;
                } catch { isActive = false; }
                // CRASH-5: burnout score computed from most-recent survey session
                const latestWithSurvey = pSessions.filter(s=>s?.survey).slice(-1)[0];
                const burnout = calcBurnout(latestWithSurvey);
                const burnoutColor = burnout === null ? T.muted
                  : burnout >= 70 ? T.red
                  : burnout >= 45 ? T.orange
                  : T.green;
                return (
                  <tr key={p.id} style={{borderBottom:`1px solid ${T.faint}`,transition:"background .15s"}}
                    onMouseEnter={e=>e.currentTarget.style.background="rgba(99,179,237,0.04)"}
                    onMouseLeave={e=>e.currentTarget.style.background=""}>
                    <td style={{padding:"9px 12px",fontFamily:T.mono,color:T.teal,fontSize:11,whiteSpace:"nowrap"}}>{p.id}</td>
                    <td style={{padding:"9px 12px",color:T.muted}}>{p.grade ?? "—"}</td>
                    <td style={{padding:"9px 12px",color:T.muted}}>{p.ageRange ?? "—"}</td>
                    <td style={{padding:"9px 12px",color:T.muted,whiteSpace:"nowrap"}}>{p.joinedDate ?? "—"}</td>
                    <td style={{padding:"9px 12px",fontWeight:600,color:T.text,textAlign:"center"}}>{pSessions.length}</td>
                    <td style={{padding:"9px 12px",color:T.muted,whiteSpace:"nowrap"}}>{lastDate}</td>
                    <td style={{padding:"9px 12px"}}>
                      <span style={{background:isActive?"rgba(104,211,145,0.12)":"rgba(45,55,72,0.6)",
                                    color:isActive?T.green:T.muted,
                                    padding:"3px 10px",borderRadius:20,fontSize:10,fontWeight:500}}>
                        {isActive?"● Active":"○ Inactive"}
                      </span>
                    </td>
                    <td style={{padding:"9px 12px"}}>
                      {burnout !== null
                        ? <span style={{background:`${burnoutColor}18`,color:burnoutColor,
                                        padding:"3px 10px",borderRadius:20,fontSize:11,fontWeight:600}}>
                            {burnout}
                          </span>
                        : <span style={{color:T.muted,fontSize:11}}>—</span>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
