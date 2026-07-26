import InlineLoadingIndicator from './InlineLoadingIndicator.jsx';

export default function ButtonSpinner({ size = 16 }) {
  return (
    <span
      className="button-spinner"
      data-testid="button-spinner"
      style={{ display: 'inline-flex', verticalAlign: 'middle', marginRight: 6 }}
      aria-hidden="true"
    >
      <InlineLoadingIndicator size={size} label="" />
    </span>
  );
}
