/**
 * Verbatim presentation content for the NeuroCortex public homepage.
 * Wording must match the approved presentation exactly — do not edit here without source approval.
 */

// PAGE 1 — OPENING (also PAGE 13 — CLOSING)
export const openingSlide = {
  kicker: 'Science Fair Project Presentation',
  title:
    'NeuroCortex: A predictive model capable of detecting cognitive overload and burnout early using passive digital biomarkers and personalized AI models',
  author: 'By Yash Gupta',
  school: 'Jose Marti STEM Academy',
};

// PAGE 2 — RESEARCH QUESTION
export const researchQuestion = {
  heading: 'RESEARCH QUESTION',
  text: 'Can NeuroCortex predict cognitive overload and burnout earlier than the appearance of noticeable symptoms in students?',
};

// PAGE 3 — HYPOTHESIS
export const hypothesis = {
  heading: 'HYPOTHESIS',
  text: "Shifts in digital behavior can occur in a student's day before self-reported burnout or cognitive overload",
};

// PAGES 4–5 — BACKGROUND INFORMATION
export const backgroundInformation = {
  agenda: 'AGENDA',
  heading: 'BACKGROUND INFORMATION',
  paragraphs: [
    'Researchers found that continuously collected smartphone behavior can be used to build personalized models that predict changes in mood and mental health over long periods, highlighting the value of individualized digital biomarkers for early detection.',
    'Personalized machine learning models that continuously learn from individual behavioral data improve the prediction of changes in mental health and support (just-in-time) interventions.',
    'Smartphones represent an ideal platform for fatigue monitoring due to their ubiquity, array of embedded sensors, and computational capabilities.',
    'Research shows that cognitive overload is one of the earliest signs of burnout and can be measured before obvious symptoms appear. By combining passive digital biomarkers with personalized AI models, it may be possible to identify students at risk earlier and provide support before burnout affects their learning, well-being, and academic performance.',
  ],
};

// PAGE 6 — PROBLEM
export const problem = {
  heading: 'PROBLEM',
  statements: [
    'A global problem is stress overload.',
    'This leads to 2.8 million deaths annually.',
    'This is due to a lack of understanding of the causes that initiate cognitive overload and burnout.',
    'Technologies have been developed to assist in reducing stress after it has reached a high level',
    'However, there aren’t many technologies that emphasize the root cause of stress',
  ],
};

// PAGE 7 — PURPOSE
export const purpose = {
  heading: 'PURPOSE',
  text: 'The purpose of this project is to detect cognitive overload and stress burnout days before the detection of noticeable symptoms appear. An AI model was developed to supply information to users and was trained on data from human participants to ensure the information and numbers are as accurate as possible.',
};

// PAGE 8 — MATERIALS
export const materials = {
  heading: 'MATERIALS',
  humanParticipants: '1. Human Participants',
  computerTitle: '2.Computer - HP EliteBook 840 G3',
  specifications: [
    'Processor: Intel Core i7 6th-Gen (i7-6500U or i7-6600U).',
    'Memory & Storage: Supports up to 32GB DDR4 RAM and fast M.2 NVMe SSDs.',
    'Display: 14-inch screen, typically Full HD (1080p) or QHD (1440p) resolution.',
    'Operating System: Windows 10 Version 22H2.',
  ],
};

// PAGE 9 — PROCEDURE
export const procedure = {
  heading: 'PROCEDURE',
  stages: [
    {
      title: 'Build the App',
      steps: [
        'a. Create all pages',
        'b. Set up the database',
        'c. Build reaction-time tests',
        'd. Build typing tests',
        'e. Build memory tests',
        'f. Build surveys',
        'g. Build data export tools',
        'h. Fix bugs',
      ],
    },
    {
      title: 'Recruit Participants',
      steps: [
        'a. Get consent forms signed',
        'b. Assign participant IDs',
        'c. Explain the study',
        'd. Show participants how to use the app',
      ],
    },
    {
      title: 'Collect Data',
      steps: [
        'a. Open app',
        'b. Complete tests',
        'c. Fill out surveys',
      ],
    },
    {
      title: 'Analyze Data',
      steps: [
        'a. Clean data',
        'b. Engineer features',
        'c. Train AI models',
        'd. Compare models',
      ],
    },
    {
      title: 'Draw Conclusion',
      steps: [
        'a. Display to users recommendation',
        'b. Display to users the likeness of stress and cognitive overload',
      ],
    },
  ],
};

// PAGE 10 — FUTURE WORKS
export const futureWorks = {
  heading: 'FUTURE WORKS',
  numbers: ['01', '02', '03', '04'],
};

// PAGE 11 — CONCLUSION
export const conclusion = {
  heading: 'CONCLUSION',
};

// PAGE 12 — BIBLIOGRAPHY
export const bibliography = {
  heading: 'BIBLIOGRAPHY',
  entries: [
    'Balliu, Brunilda, et al. "Personalized Mood Prediction from Patterns of Behavior Collected with Smartphones." npj Digital Medicine, vol. 7, no. 49, 28 Feb. 2024, doi.org.',
    '"Digital Biomarkers and AI for Remote Monitoring of Fatigue in Neurological Disorders." PubMed Central (PMC), National Center for Biotechnology Information, 21 May 2025, pmc.ncbi.nlm.nih.gov/articles/PMC12110069/.',
    '"Stress, Overtime, Disease, Contribute to 2.8 Million Workers\' Deaths per Year, Reports UN Labour Agency." UN News, United Nations, 18 Apr. 2019, news.un.org/en/story/2019/04/1036851.',
    'Wang, Shirley B., et al. "Building Personalized Machine Learning Models Using Real-Time Monitoring Data to Predict Idiographic Suicidal Thoughts." Nature Mental Health, vol. 2, 24 Oct. 2024, https://doi.org/10.1038/s44220-024-00335-w.',
    'Zhao, Lin, et al. "Development and Validation of a Digital Burnout Scale in Artificial Intelligence Era." Frontiers in Psychology, vol. 16, 13 Jan. 2026, doi.org.',
  ],
};

export const sectionNav = [
  { id: 'home', label: 'Home' },
  { id: 'research-question', label: 'Research' },
  { id: 'background', label: 'Background' },
  { id: 'procedure', label: 'Method' },
  { id: 'future-works', label: 'Future Works' },
  { id: 'bibliography', label: 'Sources' },
];

/** Flat list of required verbatim strings for content-audit tests. */
export function allRequiredVerbatimStrings() {
  return [
    openingSlide.kicker,
    openingSlide.title,
    openingSlide.author,
    openingSlide.school,
    researchQuestion.heading,
    researchQuestion.text,
    hypothesis.heading,
    hypothesis.text,
    backgroundInformation.agenda,
    backgroundInformation.heading,
    ...backgroundInformation.paragraphs,
    problem.heading,
    ...problem.statements,
    purpose.heading,
    purpose.text,
    materials.heading,
    materials.humanParticipants,
    materials.computerTitle,
    ...materials.specifications,
    procedure.heading,
    ...procedure.stages.flatMap(stage => [stage.title, ...stage.steps]),
    futureWorks.heading,
    ...futureWorks.numbers,
    conclusion.heading,
    bibliography.heading,
    ...bibliography.entries,
  ];
}
