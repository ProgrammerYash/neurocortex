import { useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import HomeNavbar from './HomeNavbar.jsx';
import HomeFooter from './HomeFooter.jsx';
import WorkInProgressPanel from './WorkInProgressPanel.jsx';
import PurposeFlowDiagram from './PurposeFlowDiagram.jsx';
import { HeroBrainVisual, useReveal } from './homeUtils.jsx';
import {
  backgroundInformation,
  bibliography,
  conclusion,
  futureWorks,
  hypothesis,
  materials,
  openingSlide,
  problem,
  procedure,
  purpose,
  researchQuestion,
  workInProgressLabel,
} from '../../content/presentationContent.js';
import { ROUTES } from '../../routing/routePaths.js';
import './home.css';

export default function PublicHome() {
  const pageRef = useReveal();
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (!location.hash) return;
    const id = location.hash.replace('#', '');
    if (!id) return;
    const timer = window.setTimeout(() => {
      document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
    }, 50);
    return () => window.clearTimeout(timer);
  }, [location.pathname, location.hash]);

  const scrollToResearch = () => {
    document.getElementById('research-question')?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div className="home-page" ref={pageRef}>
      <HomeNavbar />
      <main>
        <section id="home" className="home-hero" aria-labelledby="home-title">
          <div className="home-hero__grid">
            <div className="home-reveal">
              <p className="home-hero__kicker">{openingSlide.kicker}</p>
              <h1 id="home-title" className="home-hero__title">{openingSlide.title}</h1>
              <div className="home-hero__meta">
                <p>{openingSlide.author}</p>
                <p>{openingSlide.school}</p>
              </div>
              <div className="home-hero__actions">
                <button type="button" className="home-btn" onClick={scrollToResearch}>Explore the Research</button>
                <button type="button" className="home-btn home-btn--primary" onClick={() => navigate(ROUTES.join)}>Join the Study</button>
                <button type="button" className="home-btn" onClick={() => navigate(ROUTES.participantSignIn)}>Participant Sign In</button>
              </div>
            </div>
            <div className="home-reveal">
              <HeroBrainVisual />
            </div>
          </div>
        </section>

        <section id="research-question" className="home-section" aria-labelledby="research-question-title">
          <div className="home-section__inner home-reveal">
            <h2 id="research-question-title" className="home-section__title">{researchQuestion.heading}</h2>
            <div className="home-card home-card--centered home-card--hover home-card--statement" style={{ borderColor: 'rgba(45,212,191,0.35)', boxShadow: '0 0 40px rgba(45,212,191,0.08)' }}>
              <p style={{ fontSize: 'clamp(1.1rem, 2.5vw, 1.45rem)', lineHeight: 1.65 }}>{researchQuestion.text}</p>
            </div>
          </div>
        </section>

        <section id="hypothesis" className="home-section" aria-labelledby="hypothesis-title">
          <div className="home-section__inner home-reveal">
            <h2 id="hypothesis-title" className="home-section__title">{hypothesis.heading}</h2>
            <div className="home-card home-card--centered home-card--hover home-card--statement">
              <p style={{ fontSize: 'clamp(1.1rem, 2.5vw, 1.45rem)', lineHeight: 1.65 }}>{hypothesis.text}</p>
            </div>
          </div>
        </section>

        <section id="background" className="home-section" aria-labelledby="background-title">
          <div className="home-section__inner home-reveal">
            <h2 id="background-title" className="home-section__title">{backgroundInformation.heading}</h2>
            <div className="home-grid-2">
              {backgroundInformation.paragraphs.map(paragraph => (
                <div key={paragraph.slice(0, 48)} className="home-card home-card--centered home-card--hover">
                  <p style={{ lineHeight: 1.75 }}>{paragraph}</p>
                </div>
              ))}
            </div>
            <WorkInProgressPanel label={workInProgressLabel} />
          </div>
        </section>

        <section id="problem" className="home-section" aria-labelledby="problem-title">
          <div className="home-section__inner home-reveal">
            <h2 id="problem-title" className="home-section__title">{problem.heading}</h2>
            <div className="home-grid-2 home-problem-grid">
              {problem.statements.map((statement, index) => (
                <div
                  key={statement}
                  className={`home-card home-card--centered-problem home-card--hover${index === problem.statements.length - 1 ? ' problem-card--wide' : ''}`}
                >
                  <p style={{ lineHeight: 1.75 }}>{statement}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="purpose" className="home-section" aria-labelledby="purpose-title">
          <div className="home-section__inner home-reveal">
            <h2 id="purpose-title" className="home-section__title">{purpose.heading}</h2>
            <div className="home-grid-2">
              <div className="home-card home-card--centered home-card--hover">
                <p style={{ lineHeight: 1.75 }}>{purpose.text}</p>
              </div>
              <div className="home-card home-card--centered home-card--flow home-card--hover">
                <PurposeFlowDiagram />
              </div>
            </div>
          </div>
        </section>

        <section id="materials" className="home-section" aria-labelledby="materials-title">
          <div className="home-section__inner home-reveal">
            <h2 id="materials-title" className="home-section__title">{materials.heading}</h2>
            <div className="home-grid-2">
              <div className="home-card home-card--centered home-card--hover">
                <p style={{ fontWeight: 600 }}>{materials.humanParticipants}</p>
              </div>
              <div className="home-card home-card--centered home-card--materials-spec home-card--hover">
                <p style={{ fontWeight: 600, marginBottom: 14 }}>{materials.computerTitle}</p>
                <ul style={{ paddingLeft: 18, lineHeight: 1.85, margin: 0 }}>
                  {materials.specifications.map(spec => (
                    <li key={spec}>{spec}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </section>

        <section id="procedure" className="home-section" aria-labelledby="procedure-title">
          <div className="home-section__inner home-reveal">
            <h2 id="procedure-title" className="home-section__title">{procedure.heading}</h2>
            <div className="home-procedure-roadmap">
              {procedure.stages.map((stage, index) => (
                <div key={stage.title} className={`home-card home-procedure-card home-card--hover${index === 0 ? ' home-procedure-card--current' : ''}`}>
                  {index === 0 ? (
                    <div className="home-procedure-badge">
                      <span className="home-procedure-badge__label">CURRENT PHASE</span>
                      <span className="home-procedure-badge__sub">We are here</span>
                    </div>
                  ) : null}
                  <div className="home-procedure-phase">{procedure.phaseLabels[index]}</div>
                  <h3 style={{ fontSize: 16, marginBottom: 12 }}>{stage.title}</h3>
                  <ul style={{ paddingLeft: 16, lineHeight: 1.8, fontSize: 14, margin: 0 }}>
                    {stage.steps.map(step => (
                      <li key={step}>{step}</li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="future-works" className="home-section" aria-labelledby="future-works-title">
          <div className="home-section__inner home-reveal">
            <h2 id="future-works-title" className="home-section__title">{futureWorks.heading}</h2>
            <WorkInProgressPanel label={workInProgressLabel} />
          </div>
        </section>

        <section id="conclusion" className="home-section" aria-labelledby="conclusion-title">
          <div className="home-section__inner home-reveal">
            <h2 id="conclusion-title" className="home-section__title">{conclusion.heading}</h2>
            <WorkInProgressPanel size="large" label={workInProgressLabel} />
          </div>
        </section>

        <section id="bibliography" className="home-section" aria-labelledby="bibliography-title">
          <div className="home-section__inner home-reveal">
            <h2 id="bibliography-title" className="home-section__title">{bibliography.heading}</h2>
            <ol className="home-bibliography-list" style={{ paddingLeft: 20 }}>
              {bibliography.entries.map(entry => (
                <li key={entry} className="home-bibliography-item home-card home-card--centered home-card--hover" style={{ listStyle: 'decimal' }}>
                  {entry}
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="home-closing" aria-labelledby="closing-title">
          <div className="home-section__inner home-reveal">
            <p className="home-hero__kicker">{openingSlide.kicker}</p>
            <h2 id="closing-title" className="home-hero__title" style={{ fontSize: 'clamp(1.35rem, 3vw, 2rem)' }}>{openingSlide.title}</h2>
            <div className="home-hero__meta">
              <p>{openingSlide.author}</p>
              <p>{openingSlide.school}</p>
            </div>
          </div>
        </section>

        <section id="join-study" className="home-cta">
          <div className="home-cta__inner home-reveal">
            <div className="home-cta__actions">
              <button type="button" className="home-btn home-btn--primary" onClick={() => navigate(ROUTES.join)}>Join the Study</button>
              <button type="button" className="home-btn" onClick={() => navigate(ROUTES.participantSignIn)}>Participant Sign In</button>
              <Link to={ROUTES.home} className="home-btn" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>Back to Top</Link>
            </div>
          </div>
        </section>
      </main>
      <HomeFooter />
    </div>
  );
}
