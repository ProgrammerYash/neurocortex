import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ConsentWizard from './ConsentWizard.jsx';
import { fetchCurrentConsent } from '../../store/consent.js';

vi.mock('../../store/consent.js', () => ({ fetchCurrentConsent: vi.fn() }));

const consent = {
  consent_version: 'v1',
  survey_version: 's1',
  template_sha256: 'abc',
  student_researcher: 'Student',
  project_title: 'Project',
  purpose: 'Purpose text',
  participation_activities: 'Activities',
  time_required: 'Time',
  potential_risks: 'Risks',
  potential_benefits: 'Benefits',
  confidentiality: 'Confidential',
  questions_contact: 'Contact',
  adult_sponsor: 'Sponsor',
  adult_sponsor_contact: 'Sponsor contact',
  voluntary_participation: 'Voluntary',
  may_stop: 'Stop',
  may_skip_questions: 'Skip',
  signing_explanation: 'Sign',
  participant_acknowledgment: 'Participant approved words',
  guardian_acknowledgment: 'Guardian approved words',
};

describe('ConsentWizard typed signatures', () => {
  beforeEach(() => fetchCurrentConsent.mockResolvedValue(consent));

  it('uses typed signature previews and requires agreement checkboxes', async () => {
    let resolve;
    const onSubmit = vi.fn(() => new Promise(done => { resolve = done; }));
    render(<ConsentWizard onSubmit={onSubmit} />);
    fireEvent.change(await screen.findByLabelText('Participant legal printed name'), { target: { value: 'Student Name' } });
    fireEvent.change(screen.getByLabelText('Guardian legal printed name'), { target: { value: 'Guardian Name' } });
    fireEvent.click(screen.getByRole('button', { name: /Read Consent Form/ }));
    fireEvent.click(screen.getByRole('button', { name: /Participant Review/ }));
    expect(screen.queryByLabelText('Participant signature')).not.toBeInTheDocument();
    expect(screen.getByTestId('participant-typed-signature')).toHaveTextContent('Student Name');
    const participantNext = screen.getByRole('button', { name: /Guardian Review/ });
    expect(participantNext).toBeDisabled();
    fireEvent.click(screen.getByLabelText('Participant acknowledgment'));
    fireEvent.click(within(screen.getByTestId('participant-typed-signature')).getByRole('checkbox'));
    await waitFor(() => expect(participantNext).not.toBeDisabled());
    fireEvent.click(participantNext);
    expect(screen.getByTestId('guardian-typed-signature')).toHaveTextContent('Guardian Name');
    fireEvent.click(screen.getByLabelText('Guardian acknowledgment'));
    fireEvent.click(within(screen.getByTestId('guardian-typed-signature')).getByRole('checkbox'));
    fireEvent.click(screen.getByRole('button', { name: /Final Review/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Submit Consent' }));
    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit.mock.calls[0][0]).toMatchObject({
      participantPrintedName: 'Student Name',
      guardianPrintedName: 'Guardian Name',
      participantSignatureAgreed: true,
      guardianSignatureAgreed: true,
    });
    resolve();
    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
  });
});
