import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import ConsentStatusTab from './ConsentStatusTab.jsx';
import { fetchMyConsentStatus } from '../../store/consent.js';

vi.mock('../../store/consent.js',()=>({
  fetchMyConsentStatus:vi.fn(),
  requestDataDeletion:vi.fn(),
  withdrawParticipation:vi.fn(),
}));

describe('ConsentStatusTab',()=>{
  it('shows recorded status and no legacy or PDF controls',async()=>{
    fetchMyConsentStatus.mockResolvedValue({consent_recorded:true,session_eligible:true,withdrawal_status:'active',deletion_requested:false});
    render(<ConsentStatusTab/>);
    expect(await screen.findByText('Recorded')).toBeInTheDocument();
    expect(screen.queryByText(/Participant assent/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Parental permission/i)).not.toBeInTheDocument();
    expect(screen.queryByRole('button',{name:/pdf/i})).not.toBeInTheDocument();
  });
});
