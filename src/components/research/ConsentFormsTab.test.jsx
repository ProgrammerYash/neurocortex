import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ConsentFormsTab from './ConsentFormsTab.jsx';
import { downloadAllConsents, downloadConsent, fetchConsentPdf, fetchResearcherConsents } from '../../store/consent.js';

vi.mock('../../store/consent.js',()=>({
  fetchResearcherConsents:vi.fn(),
  fetchConsentPdf:vi.fn(),
  downloadConsent:vi.fn(),
  downloadAllConsents:vi.fn(),
}));

describe('ConsentFormsTab',()=>{
  beforeEach(()=>{
    fetchResearcherConsents.mockResolvedValue({items:[{id:'c1',participant_id:'NC-1',participant_printed_name:'Student',guardian_printed_name:'Guardian',participant_signed_at:'2026-01-01',guardian_signed_at:'2026-01-01',consent_version:'v1',survey_version:'s1',status:'recorded'}],total:1,limit:20,offset:0});
    fetchConsentPdf.mockResolvedValue({blob:new Blob(['pdf']),filename:'form.pdf'});
    downloadConsent.mockResolvedValue({blob:new Blob(['pdf']),filename:'form.pdf'});
    downloadAllConsents.mockResolvedValue({blob:new Blob(['zip']),filename:'forms.zip'});
    URL.createObjectURL=vi.fn(()=> 'blob:test');
    URL.revokeObjectURL=vi.fn();
    window.open=vi.fn();
    HTMLAnchorElement.prototype.click=vi.fn();
  });
  it('loads forms and performs authenticated blob actions',async()=>{
    render(<ConsentFormsTab/>);
    expect(await screen.findByText('NC-1')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'View'}));
    await waitFor(()=>expect(fetchConsentPdf).toHaveBeenCalledWith('c1'));
    expect(window.open).toHaveBeenCalledWith('blob:test','_blank','noopener,noreferrer');
    fireEvent.click(screen.getByRole('button',{name:'Download'}));
    await waitFor(()=>expect(downloadConsent).toHaveBeenCalledWith('c1'));
    fireEvent.click(screen.getByRole('button',{name:'Download All ZIP'}));
    await waitFor(()=>expect(downloadAllConsents).toHaveBeenCalled());
  });
});
