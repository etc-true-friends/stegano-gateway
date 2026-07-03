const COLORS = ['#e05c5c', '#d4c5a9', '#7ec8c8'];

export default function ExtSummary({ logs = [], rows }) {
  const top = rows
    ? rows
        .filter(row => (row.suspicious_count || 0) > 0)
        .map(row => [row.extension === 'unknown' ? '기타' : row.extension, row.suspicious_count || 0, row.avg_risk_score])
        .slice(0, 3)
    : Object.entries(logs.reduce((extCounts, log) => {
        if (log.verdict !== 'SUSPICIOUS') return extCounts;
        const name = log.original_name || '';
        const ext = name.includes('.') ? name.split('.').pop().toLowerCase() : '기타';
        extCounts[ext] = (extCounts[ext] || 0) + 1;
        return extCounts;
      }, {})).sort((a, b) => b[1] - a[1]).slice(0, 3);

  if (top.length === 0) {
    return <div className="empty-state">탐지된 파일이 없습니다</div>;
  }

  return (
    <div className="stat-grid">
      {top.map(([ext, count, avgRisk], i) => (
        <div key={ext} className="stat-card" style={{ borderTop: `3px solid ${COLORS[i % COLORS.length]}` }}>
          <div className="stat-label" style={{ color: COLORS[i % COLORS.length], marginBottom: 6 }}>
            {i === 0 ? '최다 탐지 확장자' : `${i + 1}위 확장자`}
          </div>
          <div className="stat-value" style={{ color: COLORS[i % COLORS.length] }}>
            .{ext}
          </div>
          <div style={{ marginTop: 8, fontSize: 12, color: '#64748b' }}>
            {count}건{avgRisk != null ? ` · 평균 위험도 ${Number(avgRisk).toFixed(1)}%` : ''}
          </div>
        </div>
      ))}
    </div>
  );
}
