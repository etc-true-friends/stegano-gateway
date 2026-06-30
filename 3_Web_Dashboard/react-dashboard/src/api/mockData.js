// 더미 데이터 — 나중에 실제 API 연동 시 이 파일은 사용 안 함
// useAuditLog.js 에서 API 실패 시 자동으로 이 데이터를 사용

function randomBetween(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function isoTimestamp(minutesAgo) {
  const d = new Date(Date.now() - minutesAgo * 60 * 1000);
  return d.toISOString();
}

const FILE_NAMES = [
  'photo_vacation.png',
  'report_final.jpg',
  'invoice_2024.png',
  'profile_pic.jpeg',
  'scan_doc001.bmp',
  'logo_design.png',
  'screenshot_01.png',
  'attachment_img.webp',
  'id_card_copy.jpg',
  'contract_signed.png',
  'budget_chart.png',
  'meeting_notes.jpeg',
  'product_photo.webp',
  'badge_icon.png',
  'receipt_upload.jpg',
];

const USERS = [
  'admin@gmail.com',
  'test@gmail.com',
  'security@etc-friends.local',
  'user@etc-friends.local',
];

function makeLog(minutesAgo) {
  const prob = parseFloat((Math.random() * 100).toFixed(1));
  const risk_level = prob >= 70 ? 'HIGH' : prob >= 40 ? 'MEDIUM' : 'LOW';
  const verdict = prob >= 50 ? 'SUSPICIOUS' : 'CLEAN';
  const sender_email = USERS[randomBetween(0, USERS.length - 1)];
  let recipient_email = USERS[randomBetween(0, USERS.length - 1)];
  if (recipient_email === sender_email) {
    recipient_email = USERS[(USERS.indexOf(sender_email) + 1) % USERS.length];
  }
  return {
    timestamp: isoTimestamp(minutesAgo),
    original_name: FILE_NAMES[randomBetween(0, FILE_NAMES.length - 1)],
    direction: Math.random() > 0.5 ? 'OUTBOUND' : 'INBOUND',
    sender_email,
    recipient_email,
    stego_probability: prob,
    risk_level,
    verdict,
    action: verdict === 'SUSPICIOUS' ? (prob >= 70 ? 'quarantined' : 'sanitized') : 'passed',
  };
}

// 최근 7일치 데이터 150건 생성
export const MOCK_LOGS = Array.from({ length: 150 }, (_, i) =>
  makeLog(randomBetween(i * 67, i * 67 + 67))
).sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

export const MOCK_AUDIT = {
  total_count: MOCK_LOGS.length,
  suspicious_count: MOCK_LOGS.filter(l => l.verdict === 'SUSPICIOUS').length,
  logs: MOCK_LOGS,
};

export const MOCK_SYS_INFO = {
  ai_model: 'StegoDetector-v2',
  device: 'CPU',
  version: '2.7.4 (mock)',
};

// 무해화 이력(CDR 처리) 더미 — API 실패 시 SanitizeHistoryPage가 사용
function makeCdrLog(i) {
  const before = parseFloat((Math.random() * 60 + 38).toFixed(1)); // 위험 판정만(38~98%)
  const after = parseFloat((Math.random() * 1.5).toFixed(1));      // 무해화 후 0~1.5%
  const originalKb = parseFloat((Math.random() * 800 + 120).toFixed(1));
  const sanitizedKb = parseFloat((originalKb * (Math.random() * 0.25 + 0.45)).toFixed(1));
  return {
    file_id: `mock${String(i).padStart(4, '0')}`,
    file_name: FILE_NAMES[randomBetween(0, FILE_NAMES.length - 1)],
    stego_probability: before,
    rescan_probability: after,
    processed_at: isoTimestamp(i * 53 + randomBetween(0, 40)),
    risk_level: before >= 70 ? 'HIGH' : 'MEDIUM',
    action: 'QUARANTINE',
    original_kb: originalKb,
    sanitized_kb: sanitizedKb,
    avg_pixel_diff: parseFloat((Math.random() * 6 + 1).toFixed(3)),
  };
}

export const MOCK_CDR_HISTORY = {
  total_count: 24,
  logs: Array.from({ length: 24 }, (_, i) => makeCdrLog(i)),
};
