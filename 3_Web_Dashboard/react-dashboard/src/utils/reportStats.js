import { getActionBucket, getEventDate, getVerdictBucket } from './detectionStats';

export function riskScore(log) {
  const probability = Number(log?.stego_probability);
  if (Number.isFinite(probability)) return probability;

  return {
    HIGH: 90,
    MEDIUM: 55,
    LOW: 15,
    UNKNOWN: 0,
  }[String(log?.risk_level || 'UNKNOWN').toUpperCase()] || 0;
}

export function bucketDate(date, period = 'day') {
  if (!date) return '';
  if (period === 'month') return date.slice(0, 7);
  if (period === 'week') {
    const parsed = new Date(`${date}T00:00:00`);
    if (Number.isNaN(parsed.getTime())) return date;
    const thursday = new Date(parsed);
    thursday.setDate(parsed.getDate() + 3 - ((parsed.getDay() + 6) % 7));
    const weekOne = new Date(thursday.getFullYear(), 0, 4);
    const week = 1 + Math.round(((thursday - weekOne) / 86400000 - 3 + ((weekOne.getDay() + 6) % 7)) / 7);
    return `${thursday.getFullYear()}-W${String(week).padStart(2, '0')}`;
  }
  return date;
}

function emptyDailyRow(date) {
  return {
    date,
    total_count: 0,
    clean_count: 0,
    suspicious_count: 0,
    unscanned_count: 0,
    bypass_count: 0,
    sanitized_count: 0,
    quarantine_count: 0,
    policy_count: 0,
    cdr_count: 0,
    mail_count: 0,
    other_count: 0,
    high_count: 0,
    medium_count: 0,
    low_count: 0,
    unknown_count: 0,
    riskSum: 0,
    max_risk_score: 0,
  };
}

function addCounts(row, log) {
  const verdict = getVerdictBucket(log);
  const action = getActionBucket(log);
  const level = String(log?.risk_level || 'UNKNOWN').toUpperCase();
  const score = riskScore(log);

  row.total_count += 1;
  row.riskSum += score;
  row.max_risk_score = Math.max(row.max_risk_score, score);

  if (verdict === 'clean') row.clean_count += 1;
  if (verdict === 'suspicious') row.suspicious_count += 1;
  if (verdict === 'unscanned') row.unscanned_count += 1;

  if (action === 'bypass') row.bypass_count += 1;
  if (action === 'sanitized') {
    row.sanitized_count += 1;
    row.cdr_count += 1;
  }
  if (action === 'quarantine') row.quarantine_count += 1;
  if (action === 'policy') row.policy_count += 1;
  if (action === 'mail') row.mail_count += 1;
  if (action === 'other') row.other_count += 1;

  if (level === 'HIGH') row.high_count += 1;
  else if (level === 'MEDIUM') row.medium_count += 1;
  else if (level === 'LOW') row.low_count += 1;
  else row.unknown_count += 1;
}

function finalizeRow(row) {
  const total = row.total_count;
  const avg = total > 0 ? row.riskSum / total : 0;
  const rest = { ...row };
  delete rest.riskSum;
  return {
    ...rest,
    avg_risk_score: Number(avg.toFixed(1)),
    max_risk_score: Number(row.max_risk_score.toFixed(1)),
  };
}

export function makeDailyDetectionRows(logs, period = 'day') {
  const rows = {};
  logs.forEach(log => {
    const date = bucketDate(getEventDate(log), period);
    if (!date) return;
    rows[date] ||= emptyDailyRow(date);
    addCounts(rows[date], log);
  });

  return Object.values(rows).sort((a, b) => a.date.localeCompare(b.date)).map(finalizeRow);
}

export function makeRiskTrendRows(logs, period = 'day') {
  return makeDailyDetectionRows(logs, period).map(row => ({
    bucket: row.date,
    score: row.avg_risk_score,
    avg_score: row.avg_risk_score,
    max_score: row.max_risk_score,
    total_count: row.total_count,
    suspicious_count: row.suspicious_count,
    high_count: row.high_count,
    medium_count: row.medium_count,
    low_count: row.low_count,
    cdr_count: row.cdr_count,
    policy_count: row.policy_count,
  }));
}

export function getExtension(name) {
  const fileName = String(name || '').split('::').pop().trim();
  const ext = fileName.includes('.') ? fileName.split('.').pop().toLowerCase() : '';
  return ext || 'unknown';
}

export function makeFileTypeRows(logs) {
  const rows = {};
  logs.forEach(log => {
    const extension = getExtension(log.original_name);
    const mimeType = log.attachment_mime_type || 'unknown';
    const key = `${extension}|${mimeType}`;
    rows[key] ||= {
      extension,
      mime_type: mimeType,
      ...emptyDailyRow(extension),
    };
    addCounts(rows[key], log);
  });

  return Object.values(rows)
    .map(row => {
      const finalized = finalizeRow(row);
      delete finalized.date;
      return finalized;
    })
    .sort((a, b) => b.total_count - a.total_count);
}

export function rowsToDailyTrendChart(rows) {
  return rows.map(row => ({
    date: row.date,
    clean: row.clean_count || 0,
    suspicious: row.suspicious_count || 0,
    unscanned: row.unscanned_count || 0,
    bypass: row.bypass_count || 0,
    sanitized: row.sanitized_count || row.cdr_count || 0,
    quarantine: row.quarantine_count || 0,
    policy: row.policy_count || 0,
    mail: row.mail_count || 0,
    other: row.other_count || 0,
  }));
}
