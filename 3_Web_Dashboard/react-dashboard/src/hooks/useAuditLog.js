import { useState, useEffect, useCallback } from 'react';
import { fetchAuditLog, fetchSystemInfo } from '../api/gateway';
import { MOCK_AUDIT, MOCK_SYS_INFO } from '../api/mockData';

export function useAuditLog(pollInterval = 30000) {
  const [audit, setAudit] = useState(MOCK_AUDIT);          // 초기값: 더미 데이터
  const [sysInfo, setSysInfo] = useState(MOCK_SYS_INFO);   // 초기값: 더미 데이터
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
      // API 연결 실패 → 더미 데이터 유지
      setOnline(false);
      setUsingMock(true);
      setSysInfo(MOCK_SYS_INFO);
      setAudit(MOCK_AUDIT);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, pollInterval);
    return () => clearInterval(id);
  }, [refresh, pollInterval]);

  return { audit, sysInfo, online, usingMock, loading, refresh };
}
