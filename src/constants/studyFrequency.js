export const STUDY_FREQUENCIES = [
  {
    value: 'daily',
    label: 'Daily',
    sessionsPerWeek: 7,
    description: '7 sessions per week',
  },
  {
    value: 'twice_weekly',
    label: 'Twice a Week',
    sessionsPerWeek: 2,
    description: '2 sessions per week',
  },
  {
    value: 'four_times_weekly',
    label: '4 Times a Week',
    sessionsPerWeek: 4,
    description: '4 sessions per week',
  },
  {
    value: 'weekly',
    label: 'Weekly',
    sessionsPerWeek: 1,
    description: '1 session per week',
  },
];

const byValue = new Map(STUDY_FREQUENCIES.map(item => [item.value, item]));

export function studyFrequencyLabel(value) {
  if (!value) return 'Not Selected';
  return byValue.get(value)?.label ?? 'Not Selected';
}

export function isValidStudyFrequency(value) {
  return byValue.has(value);
}
