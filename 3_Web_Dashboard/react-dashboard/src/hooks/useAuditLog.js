import { useState, useEffect, useCallback } from 'react';
import { fetchAuditLog, fetchSystemInfo } from '../api/gateway';
import { MOCK_AUDIT, MOCK_SYS_INFO } from '../api/mockData';

export function useAuditLog(pollInterval = 30000) {
  const [audit, setAudit] = useState(MOCK_AUDIT);
  const [sysInfo, setSysInfo] = useState(MOCK_SYS_INFO);
  const [online, setOnline] = useState(false);
  const [usingMock, setUsingMock] = useState(true);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const [info, log] = await Promise.all([fetchSystemInfo(), fetchAuditLog()]);
      setSysInfo(info);
      setAudit(log);
      setOnline(true);
      setUsingMock(false);
    } catch {
      setOnline(false);
      setUsingMock(true);
      setSysInfo(MOCK_SYS_INFO);
      setAudit(MOCK_AUDIT);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const firstRefresh = setTimeout(refresh, 0);
    const id = setInterval(refresh, pollInterval);
    return () => {
      clearTimeout(firstRefresh);
      clearInterval(id);
    };
  }, [refresh, pollInterval]);

  return { audit, sysInfo, online, usingMock, loading, refresh };
}
