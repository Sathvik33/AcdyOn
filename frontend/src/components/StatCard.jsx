export default function StatCard({ icon, label, value, footnote, tone, isText = false }) {
  return (
    <article className="stat-card" style={tone ? { '--tone': tone } : undefined}>
      <div className="stat-head">
        <span className="stat-icon">{icon}</span>
        <span className="stat-label">{label}</span>
      </div>
      <div className={`stat-value${isText ? ' is-text' : ''}`}>{value}</div>
      {footnote ? <div className="stat-foot">{footnote}</div> : null}
    </article>
  )
}
