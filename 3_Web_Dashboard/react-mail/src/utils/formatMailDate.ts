type FormatMailDateOptions = {
  now?: Date;
};

function isValidDate(d: Date) {
  return !Number.isNaN(d.getTime());
}

function formatRelativeKorean(target: Date, now: Date) {
  const diffMs = now.getTime() - target.getTime();
  if (diffMs < 0) return '방금 전';

  const minute = 60 * 1000;
  const hour = 60 * minute;
  const day = 24 * hour;

  if (diffMs < minute) return '방금 전';
  if (diffMs < hour) return `${Math.floor(diffMs / minute)}분 전`;
  if (diffMs < day) return `${Math.floor(diffMs / hour)}시간 전`;
  return `${Math.floor(diffMs / day)}일 전`;
}

function getKoreanDateParts(d: Date) {
  const parts = new Intl.DateTimeFormat('ko-KR', {
    month: 'numeric',
    day: 'numeric',
    weekday: 'short',
  }).formatToParts(d);

  const month = parts.find((p) => p.type === 'month')?.value ?? '';
  const day = parts.find((p) => p.type === 'day')?.value ?? '';
  const weekday = parts.find((p) => p.type === 'weekday')?.value ?? '';

  return { month, day, weekday };
}

function formatKoreanTime(d: Date) {
  return new Intl.DateTimeFormat('ko-KR', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  }).format(d);
}

/**
 * 예: "2026-06-15T17:22:55.931645+09:00" → "6월 15일 (월) 오후 11:12 (19시간 전)"
 */
export function formatMailDate(isoLike: string | null | undefined, options: FormatMailDateOptions = {}) {
  if (!isoLike) return '';
  const date = new Date(isoLike);
  if (!isValidDate(date)) return isoLike;

  const now = options.now ?? new Date();
  const { month, day, weekday } = getKoreanDateParts(date);
  const time = formatKoreanTime(date);
  const relative = formatRelativeKorean(date, now);

  if (!month || !day || !weekday) {
    return `${time} (${relative})`;
  }

  return `${month}월 ${day}일 (${weekday}) ${time} (${relative})`;
}

