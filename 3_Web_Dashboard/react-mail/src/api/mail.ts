import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

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
  status: 'SENT' | 'BLOCKED';
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
    });
    return res.data;
  } catch {
    return null;
  }
}

async function scanAttachment(file: File): Promise<ScanResult> {
  const form = new FormData();
  form.append('file', file);
  form.append('direction', 'OUTBOUND');

  const res = await axios.post<ScanResult>(`${API_BASE}/scan`, form);
  return res.data;
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

  // 첨부파일 스캔 (서버에 저장까지 완료됨)
  let status: 'SENT' | 'BLOCKED' = 'SENT';
  const scannedFiles: ScanResult[] = [];

  for (const file of attachments) {
    const result = await scanAttachment(file);
    scannedFiles.push(result);
    if (result.verdict === 'SUSPICIOUS') {
      status = 'BLOCKED';
      break;
    }
  }

  const cleanFiles = status === 'SENT' ? scannedFiles : [];

  const form = new FormData();
  form.append('sender', String(senderId));
  form.append('recipient', String(recipientId));
  form.append('subject', subject);
  form.append('body', body);
  form.append('status', status);
  form.append('parent_mail_id', String(parentMailId));

  // 파일 재전송 없이 scan 단계에서 받은 메타데이터만 전달
  if (cleanFiles.length > 0) {
    form.append('attachment_ids', JSON.stringify(cleanFiles.map(f => f.file_id)));
    form.append('attachment_filenames', JSON.stringify(cleanFiles.map(f => f.original_filename)));
    form.append('attachment_mimetypes', JSON.stringify(cleanFiles.map(f => f.mime_type)));
    form.append('attachment_sizes', JSON.stringify(cleanFiles.map(f => f.file_size)));
  }

  const res = await axios.post<SendMailResult>(`${API_BASE}/mails/send`, form);
  return { id: res.data.id, status };
}
