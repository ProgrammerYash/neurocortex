import Card from '../ui/Card.jsx';
import SectionTitle from '../ui/SectionTitle.jsx';
import SparkLine from '../ui/SparkLine.jsx';
import StudyProgressTab from './StudyProgressTab.jsx';
import { useParticipantTokens } from '../participant/ParticipantAppShell.jsx';

export default function ProgressTab({sessions}) {
  const P = useParticipantTokens();
  return (
    <div className="fade-in" style={{display:"flex",flexDirection:"column",gap:12}}>
      <StudyProgressTab />
      {sessions.length===0 ? (
        <Card><p style={{color:P.muted,textAlign:"center",padding:"2rem",fontSize:14}}>Complete your first session to see progress charts.</p></Card>
      ) : (
        <>
      {(() => {
        const last14 = sessions.slice(-14);
        return (
          <>
      <Card>
        <SectionTitle>Reaction Time Trend (ms)</SectionTitle>
        <SparkLine data={last14.map(s=>s.reaction?.avg||null)} color={P.teal} />
      </Card>
      <Card>
        <SectionTitle>Daily Stress Level</SectionTitle>
        <SparkLine data={last14.map(s=>s.survey?.stress||null)} color={P.red} max={10} />
      </Card>
      <Card>
        <SectionTitle>Memory Accuracy (%)</SectionTitle>
        <SparkLine data={last14.map(s=>s.memory?.accuracy||null)} color={P.purple} max={100} />
      </Card>
      <Card>
        <SectionTitle>Sleep Hours</SectionTitle>
        <SparkLine data={last14.map(s=>s.survey?.sleep||null)} color={P.blue} max={12} />
      </Card>
          </>
        );
      })()}
        </>
      )}
    </div>
  );
}
