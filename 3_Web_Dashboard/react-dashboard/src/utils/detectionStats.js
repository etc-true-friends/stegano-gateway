export function getEventDateTime(log) {
  return log?.attachment_created_at || log?.mail_sent_at || log?.timestamp || log?.mail_created_at || '';
}

export function getEventDate(log) {
  return getEventDateTime(log).slice(0, 10);
}

export function getVerdictBucket(log) {
  const verdict = String(log?.verdict || '').toUpperCase();
  if (verdict === 'SUSPICIOUS') return 'suspicious';
  if (verdict === 'CLEAN') return 'clean';
  if (verdict === 'UNSCANNED') return 'unscanned';
  return 'unknown';
}

export function getVerdictText(log) {
  return {
    suspicious: '위협',
    clean: '정상',
    unscanned: '미탐지',
    unknown: '알 수 없음',
  }[getVerdictBucket(log)];
}

export function getActionBucket(log) {
  const action = String(log?.action || '').toUpperCase();
  if (action.includes('POLICY')) return 'policy';
  if (action.includes('QUARANTINE')) return 'quarantine';
  if (action.includes('SANITIZED') || action.includes('CDR')) return 'sanitized';
  if (action === 'BYPASS' || action === 'PASSED') return 'bypass';
  if (action === 'MAIL_ATTACHMENT') return 'mail';
  return 'other';
}

export function getActionText(log) {
  return {
    policy: '정책 처리',
    quarantine: '격리',
    sanitized: 'CDR 무해화',
    bypass: '통과',
    mail: '메일 첨부',
    other: '기타',
  }[getActionBucket(log)];
}

export function formatFileSize(size) {
  const value = Number(size);
  if (!Number.isFinite(value) || value <= 0) return '-';
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}
