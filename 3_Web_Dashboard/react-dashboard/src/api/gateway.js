import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

const api = axios.create({ baseURL: API_BASE, timeout: 30000 });

export async function fetchSystemInfo() {
  const { data } = await api.get('/');
  return data;
}

export async function fetchAuditLog() {
  const { data } = await api.get('/audit');
  return data;
}

export async function scanFile(file) {
  const form = new FormData();
  form.append('file', file);
  const { data } = await api.post('/scan', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}
