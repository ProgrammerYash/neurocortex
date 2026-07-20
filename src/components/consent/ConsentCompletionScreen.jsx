import { useRef, useState } from 'react';
import { submitMyConsent } from '../../store/consent.js';
import Page from '../ui/Page.jsx';
import ConsentWizard from './ConsentWizard.jsx';

export default function ConsentCompletionScreen({onComplete,onLogout,showToast}) {
  const [submitting,setSubmitting]=useState(false);
  const [error,setError]=useState('');
  const lock=useRef(false);
  const submit=async body=>{
    if(lock.current)return;
    lock.current=true;
    setSubmitting(true);
    setError('');
    try {
      await submitMyConsent(body);
      showToast?.('Your assent and parent/guardian permission were recorded.','success');
      await onComplete();
    } catch(err) {
      setError(err.message||'Could not record consent.');
      throw err;
    } finally {
      lock.current=false;
      setSubmitting(false);
    }
  };
  return <Page title="Complete Electronic Consent" onBack={onLogout}><ConsentWizard onSubmit={submit} submitting={submitting} error={error}/></Page>;
}
