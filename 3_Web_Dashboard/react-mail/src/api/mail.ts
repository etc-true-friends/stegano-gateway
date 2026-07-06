import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';
const MAIL_REQUEST_TIMEOUT_MS = 120_000;

export type ScanVerdict = 'CLEAN' | 'SUSPICIOUS';

export type ScanResult = {
  file_id: string;
  original_filename: string;
  file_size: number;
  mime_type: string;
  verdict: ScanVerdict;
  risk_level: string;
  stego_probability: number;
};

export type SendMailResult = {
  id: number;
  status: 'SENT';
  scannedFiles: ScanResult[];
};

export type UserInfo = {
  id: number;
  email: string;
  username: string;
};

export async function findUserByEmail(email: string): Promise<UserInfo | null> {
  try {
    const res = await axios.get<UserInfo>(`${API_BASE}/users/by-email`, {
      params: { email: email.trim() },
      timeout: MAIL_REQUEST_TIMEOUT_MS,
    });
    return res.data;
  } catch {
    return null;
  }
}

export async function deleteMail(mailBoxId: number): Promise<{ id: number }> {
  const res = await axios.delete<{ id: number }>(`${API_BASE}/mails/${mailBoxId}`, {
    timeout: MAIL_REQUEST_TIMEOUT_MS,
  });
  return res.data;
}

function normalizeScanResult(file: File, result: Partial<ScanResult>): ScanResult {
  if (!result.file_id) {
    throw new Error(`첨부파일 스캔 결과에 file_id가 없습니다: ${file.name}`);
  }

  return {
    file_id: result.file_id,
    original_filename: result.original_filename || file.name,
    file_size: result.file_size ?? file.size,
    mime_type: result.mime_type || file.type || 'application/octet-stream',
    verdict: result.verdict || 'CLEAN',
    risk_level: result.risk_level || 'LOW',
    stego_probability: result.stego_probability ?? 0,
  };
}

async function scanAttachment(file: File): Promise<ScanResult> {
  const form = new FormData();
  form.append('file', file);
  form.append('direction', 'OUTBOUND');

  const res = await axios.post<ScanResult>(`${API_BASE}/scan`, form, {
    timeout: MAIL_REQUEST_TIMEOUT_MS,
  });
  console.info('[mail-send] scan response', {
    fileName: file.name,
    fileSize: file.size,
    response: res.data,
  });
  return normalizeScanResult(file, res.data);
}

export async function sendMail(params: {
  senderId: number;
  recipientId: number;
  subject: string;
  body: string;
  attachments: File[];
  parentMailId?: number;
}): Promise<SendMailResult> {
  const { senderId, recipientId, subject, body, attachments, parentMailId = 0 } = params;

  const scannedFiles: ScanResult[] = [];

  for (const file of attachments) {
    const result = await scanAttachment(file);
    scannedFiles.push(result);
  }

  const form = new FormData();
  form.append('sender', String(senderId));
  form.append('recipient', String(recipientId));
  form.append('subject', subject);
  form.append('body', body);
  form.append('status', 'SENT');
  form.append('parent_mail_id', String(parentMailId));

  if (scannedFiles.length > 0) {
    const attachmentIds = scannedFiles.map((f) => f.file_id).filter(Boolean);

    if (attachmentIds.length !== scannedFiles.length) {
      throw new Error('첨부파일 스캔 결과가 올바르지 않아 메일 전송을 중단했습니다.');
    }

    form.append('attachment_ids', JSON.stringify(attachmentIds));
    form.append('attachment_filenames', JSON.stringify(scannedFiles.map((f) => f.original_filename)));
    form.append('attachment_mimetypes', JSON.stringify(scannedFiles.map((f) => f.mime_type)));
    form.append('attachment_sizes', JSON.stringify(scannedFiles.map((f) => f.file_size)));
  }

  console.info('[mail-send] submit mail', {
    senderId,
    recipientId,
    attachmentIds: scannedFiles.map((f) => f.file_id),
  });

  const res = await axios.post<{ id: number }>(`${API_BASE}/mails/send`, form, {
    timeout: MAIL_REQUEST_TIMEOUT_MS,
  });
  return { id: res.data.id, status: 'SENT', scannedFiles };
}
