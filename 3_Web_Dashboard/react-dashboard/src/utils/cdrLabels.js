// 무해화 이력 화면에서 쓰는 실측값 포매팅 유틸.

export function formatKb(kb) {
  const value = Number(kb);
  if (!Number.isFinite(value) || value <= 0) return '-';
  if (value >= 1024) return `${(value / 1024).toFixed(1)} MB`;
  return `${value.toFixed(1)} KB`;
}

export function formatProb(prob) {
  if (prob == null || Number.isNaN(Number(prob))) return '-';
  return `${Number(prob).toFixed(1)}%`;
}

// 원본 AI 탐지율 색상
export function probColor(prob) {
  const value = Number(prob);
  if (!Number.isFinite(value)) return '#64748b';
  if (value >= 75) return '#dc2626';
  if (value >= 30) return '#d97706';
  return '#059669';
}
