import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ConsentWizard from './ConsentWizard.jsx';
import { fetchCurrentConsent } from '../../store/consent.js';

vi.mock('../../store/consent.js',()=>({fetchCurrentConsent:vi.fn()}));
const consent={consent_version:'v1',survey_version:'s1',template_sha256:'abc',student_researcher:'Student',project_title:'Project',purpose:'Purpose text',participation_activities:'Activities',time_required:'Time',potential_risks:'Risks',potential_benefits:'Benefits',confidentiality:'Confidential',questions_contact:'Contact',adult_sponsor:'Sponsor',adult_sponsor_contact:'Sponsor contact',voluntary_participation:'Voluntary',may_stop:'Stop',may_skip_questions:'Skip',signing_explanation:'Sign',participant_acknowledgment:'Participant approved words',guardian_acknowledgment:'Guardian approved words'};
const sign=canvas=>{fireEvent.pointerDown(canvas,{pointerId:1,clientX:10,clientY:10});fireEvent.pointerMove(canvas,{pointerId:1,clientX:30,clientY:30});fireEvent.pointerUp(canvas,{pointerId:1,clientX:30,clientY:30});};

describe('ConsentWizard',()=>{
  beforeEach(()=>fetchCurrentConsent.mockResolvedValue(consent));
  it('loads approved content, requires acknowledgments, and locks submit',async()=>{
    let resolve;
    const onSubmit=vi.fn(()=>new Promise(done=>{resolve=done;}));
    render(<ConsentWizard onSubmit={onSubmit}/>);
    fireEvent.change(await screen.findByLabelText('Participant legal printed name'),{target:{value:'Student Name'}});
    fireEvent.change(screen.getByLabelText('Guardian legal printed name'),{target:{value:'Guardian Name'}});
    fireEvent.click(screen.getByRole('button',{name:/Read Consent Form/}));
    expect(await screen.findByText('Purpose text')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:/Participant Review/}));
    expect(screen.getByText('Participant approved words')).toBeInTheDocument();
    expect(screen.getByText(/Signing as:/)).toHaveTextContent('Student Name');
    expect(screen.queryByLabelText('Participant legal printed name')).not.toBeInTheDocument();
    const participantNext=screen.getByRole('button',{name:/Guardian Review/});
    expect(participantNext).toBeDisabled();
    fireEvent.click(screen.getByLabelText('Participant acknowledgment'));
    sign(screen.getByLabelText('Participant signature'));
    fireEvent.click(participantNext);
    expect(screen.getByText(/Signing as parent\/guardian:/)).toHaveTextContent('Guardian Name');
    expect(screen.queryByLabelText('Guardian legal printed name')).not.toBeInTheDocument();
    fireEvent.click(screen.getByLabelText('Guardian acknowledgment'));
    sign(screen.getByLabelText('Guardian signature'));
    fireEvent.click(screen.getByRole('button',{name:/Final Review/}));
    const submit=screen.getByRole('button',{name:'Submit Consent'});
    fireEvent.click(submit);fireEvent.click(submit);
    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit.mock.calls[0][0]).toMatchObject({
      participantPrintedName:'Student Name',
      guardianPrintedName:'Guardian Name',
      participantAcknowledged:true,
      guardianAcknowledged:true,
      consentVersion:'v1',
    });
    resolve();
    await waitFor(()=>expect(onSubmit).toHaveBeenCalledTimes(1));
  });
});
