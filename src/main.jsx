import { StrictMode, Suspense, lazy } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import AppPageLoader from './components/ui/AppPageLoader.jsx';
import { bootstrapAppTheme } from './utils/bootstrapParticipantTheme.js';
import './styles/signature-font.css';

bootstrapAppTheme();

const App = lazy(() => import('./App.jsx'));

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <Suspense fallback={<AppPageLoader />}>
        <App />
      </Suspense>
    </BrowserRouter>
  </StrictMode>,
);
