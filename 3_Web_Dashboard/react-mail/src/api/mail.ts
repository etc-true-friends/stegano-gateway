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
    });
    return res.data;
  } catch {
    return null;
  }
}

export async function deleteMail(mailBoxId: number): Promise<{ id: number }> {
  const res = await axios.delete<{ id: number }>(`${API_BASE}/mails/${mailBoxId}`);
  return res.data;
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
    form.append('attachment_ids', JSON.stringify(scannedFiles.map((f) => f.file_id)));
    form.append('attachment_filenames', JSON.stringify(scannedFiles.map((f) => f.original_filename)));
    form.append('attachment_mimetypes', JSON.stringify(scannedFiles.map((f) => f.mime_type)));
    form.append('attachment_sizes', JSON.stringify(scannedFiles.map((f) => f.file_size)));
  }

  const res = await axios.post<{ id: number }>(`${API_BASE}/mails/send`, form);
  return { id: res.data.id, status: 'SENT', scannedFiles };
}
