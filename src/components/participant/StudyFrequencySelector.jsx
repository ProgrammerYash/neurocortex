import { STUDY_FREQUENCIES } from '../../constants/studyFrequency.js';

export default function StudyFrequencySelector({
  name = 'study-frequency',
  value,
  onChange,
  disabled = false,
}) {
  return (
    <div
      className="study-frequency-grid"
      role="radiogroup"
      aria-label="Study schedule"
    >
      {STUDY_FREQUENCIES.map(option => {
        const selected = value === option.value;
        return (
          <label
            key={option.value}
            className={`study-frequency-option${selected ? ' is-selected' : ''}`}
          >
            <input
              type="radio"
              name={name}
              value={option.value}
              checked={selected}
              disabled={disabled}
              onChange={() => onChange(option.value)}
            />
            <span className="study-frequency-option__title">{option.label}</span>
            <span className="study-frequency-option__meta">{option.description}</span>
            {selected ? <span className="study-frequency-option__check" aria-hidden="true">Selected</span> : null}
          </label>
        );
      })}
    </div>
  );
}
