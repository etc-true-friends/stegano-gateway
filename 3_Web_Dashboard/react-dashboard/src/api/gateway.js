import axios from 'axios';

export const API_BASE =
    import.meta.env.VITE_API_BASE || 'https://stegano.app';

const api = axios.create({
    baseURL: API_BASE,
    timeout: 30000,
});

export default api;

export async function fetchSystemInfo() {
  const { data } = await api.get('/');
  return data;
}

export async function fetchAuditLog() {
  const { data } = await api.get('/audit');
  return data;
}

export async function fetchDetectionThreshold() {
  const { data } = await api.get('/policy/threshold');
  return data;
}

export async function updateDetectionThreshold(highThreshold, mediumThreshold) {
  const { data } = await api.put('/policy/threshold', {
    high_threshold: highThreshold,
    medium_threshold: mediumThreshold,
  });
  return data;
}

export async function fetchCdrStatus() {
  const { data } = await api.get('/cdr/status');
  return data;
}

export async function scanFile(file) {
    const form = new FormData();
    form.append('file', file);

    const response = await api.post('/scan', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
        responseType: 'blob',
    });

    return {
        verdict: response.headers['x-gateway-verdict'],
        riskLevel: response.headers['x-gateway-risk-level'],
        stegoProb: response.headers['x-gateway-stego-prob'],
        fileId: response.headers['x-gateway-file-id'],
        blob: response.data,
        downloadUrl: URL.createObjectURL(response.data),
    };
}

export async function fetchThreatOverview() {
    const { data } = await api.get('/dashboard/threat-overview');
    return data;
}

export const recordThreatOverviewView = async () => {
    const response = await api.post('/dashboard/threat-overview/view');
    return response.data;
};

export const heartbeatThreatOverview = async () => {
    const response = await api.post('/dashboard/threat-overview/heartbeat');
    return response.data;
};