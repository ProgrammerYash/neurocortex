import '@testing-library/jest-dom/vitest';
import { vi } from 'vitest';

globalThis.ResizeObserver = class {
  observe() {}
  disconnect() {}
};

Object.defineProperty(HTMLCanvasElement.prototype, 'getContext', {
  value: () => ({
    clearRect: vi.fn(), beginPath: vi.fn(), moveTo: vi.fn(), lineTo: vi.fn(),
    stroke: vi.fn(), set strokeStyle(_) {}, set lineWidth(_) {},
    set lineCap(_) {}, set lineJoin(_) {},
  }),
});
HTMLCanvasElement.prototype.toDataURL = () => 'data:image/png;base64,test';
HTMLCanvasElement.prototype.setPointerCapture = vi.fn();
HTMLCanvasElement.prototype.releasePointerCapture = vi.fn();
HTMLCanvasElement.prototype.hasPointerCapture = () => false;
HTMLCanvasElement.prototype.getBoundingClientRect = () => ({left:0,top:0,width:500,height:180,right:500,bottom:180});
