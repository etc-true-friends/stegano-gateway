import { useMemo, useState } from 'react';

function toDateInputValue(date) {
  return date.toISOString().slice(0, 10);
}

export const QUICK_RANGES = [
  { label: '오늘', days: 0 },
  { label: '최근 7일', days: 6 },
  { label: '최근 30일', days: 29 },
  { label: '전체', days: null },
];

export function useDateRangeFilter(logs, defaultRangeLabel = '최근 7일') {
  const defaultRange = QUICK_RANGES.find(r => r.label === defaultRangeLabel) || QUICK_RANGES[1];
  const defaultEnd = new Date();
  const defaultStart = defaultRange.days === null ? null : new Date(Date.now() - defaultRange.days * 86400000);

  const [startDate, setStartDateRaw] = useState(defaultStart ? toDateInputValue(defaultStart) : '');
  const [endDate, setEndDateRaw] = useState(defaultStart ? toDateInputValue(defaultEnd) : '');
  const [activeRange, setActiveRange] = useState(defaultRangeLabel);

  const setStartDate = (value) => { setStartDateRaw(value); setActiveRange(''); };
  const setEndDate = (value) => { setEndDateRaw(value); setActiveRange(''); };

  const applyQuickRange = (range) => {
    setActiveRange(range.label);
    if (range.days === null) {
      setStartDateRaw('');
      setEndDateRaw('');
      return;
    }
    const end = new Date();
    const start = new Date(Date.now() - range.days * 86400000);
    setStartDateRaw(toDateInputValue(start));
    setEndDateRaw(toDateInputValue(end));
  };

  const filteredLogs = useMemo(() => {
    return logs.filter(log => {
      const logDate = (log.timestamp || '').slice(0, 10);
      if (!logDate) return false;
      if (startDate && logDate < startDate) return false;
      if (endDate && logDate > endDate) return false;
      return true;
    });
  }, [logs, startDate, endDate]);

  return {
    startDate, setStartDate,
    endDate, setEndDate,
    activeRange, applyQuickRange,
    filteredLogs,
  };
}
