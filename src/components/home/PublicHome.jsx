import HomeNavbar from './HomeNavbar.jsx';
import HomeFooter from './HomeFooter.jsx';
import { HeroVisual, useReveal } from './homeUtils.jsx';
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
} from '../../content/presentationContent.js';
import './home.css';

export default function PublicHome({ onJoinStudy, onSignIn, onResearcherAccess }) {
  const pageRef = useReveal();

  const scrollToResearch = () => {
    document.getElementById('research-question')?.scrollIntoView({ behavior: 'smooth' });
  };

  const scrollToTop = () => {
    document.getElementById('home')?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div className="home-page" ref={pageRef}>
      <HomeNavbar onJoinStudy={onJoinStudy} onSignIn={onSignIn} />
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
                <button type="button" className="home-btn home-btn--primary" onClick={onJoinStudy}>Join the Study</button>
                <button type="button" className="home-btn" onClick={onSignIn}>Participant Sign In</button>
              </div>
            </div>
            <div className="home-reveal">
              <HeroVisual />
            </div>
          </div>
        </section>

        <section id="research-question" className="home-section" aria-labelledby="research-question-title">
          <div className="home-section__inner home-reveal">
            <p className="home-section__label">{researchQuestion.heading}</p>
            <h2 id="research-question-title" className="home-section__title">{researchQuestion.heading}</h2>
            <div className="home-card" style={{ borderColor: 'rgba(45,212,191,0.35)', boxShadow: '0 0 40px rgba(45,212,191,0.08)' }}>
              <p style={{ fontSize: 'clamp(1.1rem, 2.5vw, 1.45rem)', lineHeight: 1.65 }}>{researchQuestion.text}</p>
            </div>
          </div>
        </section>

        <section id="hypothesis" className="home-section" aria-labelledby="hypothesis-title">
          <div className="home-section__inner home-reveal">
            <p className="home-section__label">{hypothesis.heading}</p>
            <h2 id="hypothesis-title" className="home-section__title">{hypothesis.heading}</h2>
            <div className="home-grid-2">
              <div className="home-card">
                <p style={{ lineHeight: 1.75 }}>{hypothesis.text}</p>
              </div>
              <div className="home-card" aria-hidden="true" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12, flexWrap: 'wrap' }}>
                <span style={{ padding: '10px 14px', borderRadius: 10, border: '1px solid rgba(45,212,191,0.3)', fontSize: 13 }}>digital behavior</span>
                <span style={{ color: '#2dd4bf' }}>→</span>
                <span style={{ padding: '10px 14px', borderRadius: 10, border: '1px solid rgba(99,179,237,0.3)', fontSize: 13 }}>self-reported burnout or cognitive overload</span>
              </div>
            </div>
          </div>
        </section>

        <section id="background" className="home-section" aria-labelledby="background-title">
          <div className="home-section__inner home-reveal">
            <p className="home-section__label">{backgroundInformation.agenda}</p>
            <h2 id="background-title" className="home-section__title">{backgroundInformation.heading}</h2>
            <div className="home-grid-2">
              {backgroundInformation.paragraphs.map(paragraph => (
                <div key={paragraph.slice(0, 48)} className="home-card">
                  <p style={{ lineHeight: 1.75 }}>{paragraph}</p>
                </div>
              ))}
            </div>
            <div className="home-expansion-panel" aria-hidden="true" />
          </div>
        </section>

        <section id="problem" className="home-section" aria-labelledby="problem-title">
          <div className="home-section__inner home-reveal">
            <h2 id="problem-title" className="home-section__title">{problem.heading}</h2>
            <div className="home-grid-2">
              {problem.statements.map(statement => (
                <div key={statement} className="home-card">
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
              <div className="home-card">
                <p style={{ lineHeight: 1.75 }}>{purpose.text}</p>
              </div>
              <div className="home-card" aria-hidden="true" style={{ fontSize: 13, lineHeight: 2, color: '#a0aec0' }}>
                <div>participant data → digital biomarkers → AI model → user information</div>
              </div>
            </div>
          </div>
        </section>

        <section id="materials" className="home-section" aria-labelledby="materials-title">
          <div className="home-section__inner home-reveal">
            <h2 id="materials-title" className="home-section__title">{materials.heading}</h2>
            <div className="home-grid-2">
              <div className="home-card">
                <p style={{ fontWeight: 600, marginBottom: 8 }}>{materials.humanParticipants}</p>
              </div>
              <div className="home-card">
                <p style={{ fontWeight: 600, marginBottom: 14 }}>{materials.computerTitle}</p>
                <ul style={{ paddingLeft: 18, lineHeight: 1.85 }}>
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
                <div key={stage.title} className="home-card">
                  <div style={{ fontSize: 12, color: '#2dd4bf', marginBottom: 8 }}>{index + 1}</div>
                  <h3 style={{ fontSize: 16, marginBottom: 12 }}>{stage.title}</h3>
                  <ul style={{ paddingLeft: 16, lineHeight: 1.8, fontSize: 14 }}>
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
            <div className="home-future-grid">
              {futureWorks.numbers.map(number => (
                <div key={number} className="home-card home-future-card">{number}</div>
              ))}
            </div>
          </div>
        </section>

        <section id="conclusion" className="home-section" aria-labelledby="conclusion-title">
          <div className="home-section__inner home-reveal">
            <div className="home-card home-conclusion-panel">
              <h2 id="conclusion-title" className="home-section__title" style={{ marginBottom: 0 }}>{conclusion.heading}</h2>
              <div className="home-conclusion-panel__space" aria-hidden="true" />
            </div>
          </div>
        </section>

        <section id="bibliography" className="home-section" aria-labelledby="bibliography-title">
          <div className="home-section__inner home-reveal">
            <h2 id="bibliography-title" className="home-section__title">{bibliography.heading}</h2>
            <ol className="home-bibliography-list" style={{ paddingLeft: 20 }}>
              {bibliography.entries.map(entry => (
                <li key={entry} className="home-bibliography-item home-card" style={{ listStyle: 'decimal' }}>
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
              <button type="button" className="home-btn home-btn--primary" onClick={onJoinStudy}>Join the Study</button>
              <button type="button" className="home-btn" onClick={onSignIn}>Participant Sign In</button>
              <button type="button" className="home-btn" onClick={scrollToTop}>Back to Top</button>
            </div>
          </div>
        </section>
      </main>
      <HomeFooter onResearcherAccess={onResearcherAccess} />
    </div>
  );
}
