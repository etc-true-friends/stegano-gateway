import { QUICK_RANGES } from '../../hooks/useDateRangeFilter';

export default function DateRangeFilter({ startDate, setStartDate, endDate, setEndDate, activeRange, applyQuickRange }) {
  return (
    <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
      <input
        type="date"
        value={startDate}
        onChange={e => setStartDate(e.target.value)}
        style={{
          padding: '7px 12px', border: '1px solid #e8e0d0', borderRadius: 6,
          fontSize: 12, color: '#1e2a4a', background: '#faf7f2', outline: 'none'
        }}
      />
      <span style={{ color: '#94a3b8', fontSize: 12 }}>부터</span>
      <input
        type="date"
        value={endDate}
        onChange={e => setEndDate(e.target.value)}
        style={{
          padding: '7px 12px', border: '1px solid #e8e0d0', borderRadius: 6,
          fontSize: 12, color: '#1e2a4a', background: '#faf7f2', outline: 'none'
        }}
      />
      <span style={{ color: '#94a3b8', fontSize: 12 }}>까지</span>
      <div style={{ display: 'flex', gap: 6, marginLeft: 'auto', flexWrap: 'wrap' }}>
        {QUICK_RANGES.map(range => (
          <button
            key={range.label}
            onClick={() => applyQuickRange(range)}
            style={{
              padding: '7px 14px', borderRadius: 6, fontSize: 11,
              fontWeight: 600, cursor: 'pointer', border: '1px solid #e8e0d0',
              background: activeRange === range.label ? '#1e2a4a' : '#faf7f2',
              color: activeRange === range.label ? '#ffffff' : '#64748b',
            }}
          >
            {range.label}
          </button>
        ))}
      </div>
    </div>
  );
}
