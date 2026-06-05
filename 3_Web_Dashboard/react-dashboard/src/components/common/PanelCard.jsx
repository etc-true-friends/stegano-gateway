export default function PanelCard({ title, children, className = '' }) {
  return (
    <div className={`panel-card ${className}`}>
      {title && <div className="panel-title">{title}</div>}
      <div className="panel-body">{children}</div>
    </div>
  );
}
