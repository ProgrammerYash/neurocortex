import { createRef } from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import SignaturePad from './SignaturePad.jsx';

function sign(canvas, start = 10) {
  fireEvent.pointerDown(canvas,{pointerId:1,clientX:start,clientY:10});
  fireEvent.pointerMove(canvas,{pointerId:1,clientX:start+20,clientY:30});
  fireEvent.pointerUp(canvas,{pointerId:1,clientX:start+20,clientY:30});
}

describe('SignaturePad',()=>{
  it('detects blank, exports PNG, and clears',()=>{
    const ref=createRef();
    render(<SignaturePad ref={ref} label="Student signature"/>);
    expect(ref.current.isBlank()).toBe(true);
    sign(screen.getByLabelText('Student signature'));
    expect(ref.current.isBlank()).toBe(false);
    expect(ref.current.toPNG()).toMatch(/^data:image\/png/);
    fireEvent.click(screen.getByRole('button',{name:'Clear'}));
    expect(ref.current.isBlank()).toBe(true);
    expect(ref.current.toPNG()).toBeNull();
  });

  it('keeps two signatures independent',()=>{
    const first=createRef(),second=createRef();
    render(<><SignaturePad ref={first} label="Participant signature"/><SignaturePad ref={second} label="Guardian signature"/></>);
    sign(screen.getByLabelText('Participant signature'));
    expect(first.current.isBlank()).toBe(false);
    expect(second.current.isBlank()).toBe(true);
  });
});
