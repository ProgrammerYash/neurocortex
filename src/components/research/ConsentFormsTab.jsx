import { useEffect, useMemo, useState } from 'react';
import { T } from '../../constants/tokens.js';
import { downloadAllConsents, downloadConsent, fetchConsentPdf, fetchResearcherConsents } from '../../store/consent.js';
import Card from '../ui/Card.jsx';
import Btn from '../ui/Btn.jsx';
import SectionTitle from '../ui/SectionTitle.jsx';

function saveBlob({blob,filename}) {
  const url=URL.createObjectURL(blob);
  const anchor=document.createElement('a');
  anchor.href=url; anchor.download=filename; anchor.click();
  setTimeout(()=>URL.revokeObjectURL(url),0);
}

export default function ConsentFormsTab() {
  const [items,setItems]=useState([]);
  const [total,setTotal]=useState(0);
  const [offset,setOffset]=useState(0);
  const [search,setSearch]=useState('');
  const [sort,setSort]=useState('participant_signed_at');
  const [direction,setDirection]=useState('desc');
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState('');
  const [busy,setBusy]=useState('');
  const limit=20;

  useEffect(()=>{
    let active=true;
    setLoading(true); setError('');
    const timer=setTimeout(()=>{
      fetchResearcherConsents({limit,offset,search,sort,direction})
        .then(data=>{if(active){setItems(Array.isArray(data.items)?data.items:[]);setTotal(Number(data.total)||0);}})
        .catch(err=>active&&setError(err.message||'Could not load consent forms.'))
        .finally(()=>active&&setLoading(false));
    },200);
    return()=>{active=false;clearTimeout(timer);};
  },[offset,search,sort,direction]);

  const rows=useMemo(()=>[...items].sort((a,b)=>{
    const result=String(a?.[sort]??'').localeCompare(String(b?.[sort]??''));
    return direction==='asc'?result:-result;
  }),[items,sort,direction]);

  const setOrdering=key=>{
    if(sort===key)setDirection(value=>value==='asc'?'desc':'asc');
    else{setSort(key);setDirection('asc');}
  };
  const view=async id=>{
    setBusy(`view-${id}`);setError('');
    try {
      const result=await fetchConsentPdf(id);
      const url=URL.createObjectURL(result.blob);
      window.open(url,'_blank','noopener,noreferrer');
      setTimeout(()=>URL.revokeObjectURL(url),60000);
    } catch(err){setError(err.message||'Could not open consent PDF.');}
    finally{setBusy('');}
  };
  const download=async id=>{
    setBusy(`download-${id}`);setError('');
    try{saveBlob(await downloadConsent(id));}catch(err){setError(err.message||'Download failed.');}finally{setBusy('');}
  };
  const downloadAll=async()=>{
    setBusy('all');setError('');
    try{saveBlob(await downloadAllConsents());}catch(err){setError(err.message||'ZIP download failed.');}finally{setBusy('');}
  };

  const columns=[['participant_id','Participant ID'],['participant_printed_name','Participant name'],['guardian_printed_name','Guardian name'],['participant_signed_at','Participant signed'],['guardian_signed_at','Guardian signed'],['consent_version','Consent'],['survey_version','Survey'],['status','Status']];
  return <Card className="fade-in">
    <div style={{display:'flex',justifyContent:'space-between',gap:12,alignItems:'center',marginBottom:14,flexWrap:'wrap'}}>
      <SectionTitle>Consent Forms</SectionTitle>
      <Btn onClick={downloadAll} disabled={busy==='all'||loading} primary>{busy==='all'?'Preparing ZIP…':'Download All ZIP'}</Btn>
    </div>
    <input aria-label="Search consent forms" placeholder="Search participant ID or student name…" value={search} onChange={e=>{setSearch(e.target.value);setOffset(0);}} style={{marginBottom:12}}/>
    {error&&<p role="alert" style={{color:T.red,fontSize:13,marginBottom:12}}>{error}</p>}
    {loading?<p style={{color:T.muted,padding:20,textAlign:'center'}}>Loading consent forms…</p>:(
      <div style={{overflowX:'auto'}}>
        <table style={{width:'100%',borderCollapse:'collapse',fontSize:11}}>
          <thead><tr>{columns.map(([key,label])=><th key={key}><button onClick={()=>setOrdering(key)} style={{background:'none',color:T.muted,padding:'8px 5px',whiteSpace:'nowrap'}}>{label}{sort===key?(direction==='asc'?' ↑':' ↓'):''}</button></th>)}<th style={{color:T.muted}}>Actions</th></tr></thead>
          <tbody>{rows.map(row=><tr key={row.id} style={{borderTop:`1px solid ${T.faint}`}}>
            {columns.map(([key])=><td key={key} style={{padding:'9px 5px',whiteSpace:'nowrap'}}>{key.endsWith('_at')&&row[key]?new Date(row[key]).toLocaleString():row[key]??'—'}</td>)}
            <td style={{padding:'9px 5px',whiteSpace:'nowrap'}}><Btn onClick={()=>view(row.id)} disabled={!!busy} style={{fontSize:11,padding:'5px 8px'}}>View</Btn> <Btn onClick={()=>download(row.id)} disabled={!!busy} style={{fontSize:11,padding:'5px 8px'}}>Download</Btn></td>
          </tr>)}</tbody>
        </table>
        {!rows.length&&<p style={{color:T.muted,textAlign:'center',padding:20}}>No consent forms found.</p>}
      </div>
    )}
    <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginTop:14}}>
      <Btn onClick={()=>setOffset(Math.max(0,offset-limit))} disabled={offset===0||loading}>Previous</Btn>
      <span style={{fontSize:12,color:T.muted}}>{total?`${offset+1}–${Math.min(offset+limit,total)} of ${total}`:'0 records'}</span>
      <Btn onClick={()=>setOffset(offset+limit)} disabled={offset+limit>=total||loading}>Next</Btn>
    </div>
  </Card>;
}
