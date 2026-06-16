import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

export type ScanVerdict = 'CLEAN' | 'SUSPICIOUS';

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

async function scanAttachment(file: File): Promise<ScanVerdict> {
  const form = new FormData();
  form.append('file', file);
  form.append('direction', 'OUTBOUND');

  const res = await axios.post(`${API_BASE}/scan`, form, {
    responseType: 'blob',
  });

  const verdict = res.headers['x-gateway-verdict'] as string;
  return verdict === 'SUSPICIOUS' ? 'SUSPICIOUS' : 'CLEAN';
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

  // 첨부파일 스캔
  let status: 'SENT' | 'BLOCKED' = 'SENT';
  for (const file of attachments) {
    const verdict = await scanAttachment(file);
    if (verdict === 'SUSPICIOUS') {
      status = 'BLOCKED';
      break;
    }
  }

  const form = new FormData();
  form.append('sender_id', String(senderId));
  form.append('recipient_id', String(recipientId));
  form.append('subject', subject);
  form.append('body', body);
  form.append('status', status);
  form.append('parent_mail_id', String(parentMailId));

  // SENT인 경우에만 첨부파일 전송
  if (status === 'SENT') {
    for (const file of attachments) {
      form.append('attachments', file);
    }
  }

  const res = await axios.post<SendMailResult>(`${API_BASE}/mails/send`, form);
  return { id: res.data.id, status };
}
