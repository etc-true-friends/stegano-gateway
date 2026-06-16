import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

export type MailListItem = {
  id: number;
  sender: string;
  subject: string;
  preview: string;
  date: string;
  unread: boolean;
  avatarColor?: string;
};

export type InboxCountResponse = {
  inboxCount: number;
};

/**
 * @function 받은 메일함 리스트
 * @writer jhm
 * @param username (유저명 -> 후에 세션 작업 정리되면 고유값 [id]로 변경할 예정입니다)
 * @returns 
 */
export async function fetchInboxMails(username: string): Promise<MailListItem[]> {
  const { data } = await api.get<MailListItem[]>('/mails/inbox', {
    params: { username },
  });
  return data;
}

/**
 * @function 받은 메일 읽음 처리
 * @param mailId
 * @returns
 */
export async function markMailAsRead(mailId: number): Promise<void> {
  await api.patch(`/mails/${mailId}/read`);
}

/**
 * @function 보낸 메일함 리스트
 * @writer jhm
 * @param username (유저명 -> 후에 세션 작업 정리되면 고유값 [id]로 변경할 예정입니다)
 * @returns 
 */
export async function fetchSentMails(username: string): Promise<MailListItem[]> {
  const { data } = await api.get<MailListItem[]>('/mails/sent', {
    params: { username },
  });
  return data;
}

/**
 * @function 받은 메일함 개수
 * @param username (유저명 -> 후에 세션 작업 정리되면 고유값 [id]로 변경할 예정입니다)
 * @writer JHM
 * @returns 
 */
export async function fetchInboxCount(username: string): Promise<InboxCountResponse> {
  const { data } = await api.get<InboxCountResponse>('/mails/inbox/count', {
    params: { username },
  });
  return data;
}

