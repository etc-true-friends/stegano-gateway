import { useEffect, useState } from 'react';
import PanelCard from '../components/common/PanelCard';
import { fetchDetectionThreshold, updateDetectionThreshold } from '../api/gateway';

export default function ThresholdSettingsPage() {
  const [highThreshold, setHighThreshold] = useState(75);
  const [mediumThreshold, setMediumThreshold] = useState(30);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    fetchDetectionThreshold()
      .then(data => {
        setHighThreshold(data.high_threshold);
        setMediumThreshold(data.medium_threshold);
      })
      .catch(() => setMessage({ type: 'error', text: '임계값을 불러오지 못했습니다. 서버 연결을 확인해주세요.' }))
      .finally(() => setLoading(false));
  }, []);

  const isValid = mediumThreshold >= 0 && mediumThreshold < highThreshold && highThreshold <= 100;

  const handleSave = async () => {
    if (!isValid) {
      setMessage({ type: 'error', text: '의심(MEDIUM) 임계값은 격리(HIGH) 임계값보다 작아야 합니다.' });
      return;
    }
    setSaving(true);
    setMessage(null);
    try {
      await updateDetectionThreshold(highThreshold, mediumThreshold);
      setMessage({ type: 'success', text: '임계값이 저장되었습니다.' });
    } catch {
      setMessage({ type: 'error', text: '저장에 실패했습니다. 서버 연결을 확인해주세요.' });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="page-content"><div className="empty-state">불러오는 중...</div></div>;
  }

  return (
    <div className="page-content" style={{ maxWidth: 640 }}>
      <PanelCard title="탐지 임계값 설정">
        <p style={{ fontSize: 12, color: '#64748b', marginTop: 0, marginBottom: 20 }}>
          스테가노그래피 탐지 확률(%)에 따라 위험도 등급과 처리 방식(격리/통과)을 결정하는 기준값입니다.
        </p>

        <div style={{ marginBottom: 28 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
            <label style={{ fontSize: 13, fontWeight: 600, color: '#e05c5c' }}>격리(HIGH) 임계값</label>
            <span style={{ fontSize: 13, fontWeight: 700, color: '#e05c5c' }}>{highThreshold}%</span>
          </div>
          <input
            type="range"
            min={0}
            max={100}
            step={1}
            value={highThreshold}
            onChange={e => setHighThreshold(Number(e.target.value))}
            style={{ width: '100%' }}
          />
          <p style={{ fontSize: 11, color: '#94a3b8', marginTop: 6 }}>
            탐지 확률이 이 값 이상이면 위험도 HIGH로 분류되어 즉시 격리(QUARANTINE)됩니다.
          </p>
        </div>

        <div style={{ marginBottom: 28 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
            <label style={{ fontSize: 13, fontWeight: 600, color: '#d4a23a' }}>의심(MEDIUM) 임계값</label>
            <span style={{ fontSize: 13, fontWeight: 700, color: '#d4a23a' }}>{mediumThreshold}%</span>
          </div>
          <input
            type="range"
            min={0}
            max={100}
            step={1}
            value={mediumThreshold}
            onChange={e => setMediumThreshold(Number(e.target.value))}
            style={{ width: '100%' }}
          />
          <p style={{ fontSize: 11, color: '#94a3b8', marginTop: 6 }}>
            탐지 확률이 이 값 이상이면 위험도 MEDIUM으로 분류되어 격리(QUARANTINE)됩니다. HIGH 임계값보다 작아야 합니다.
          </p>
        </div>

        {message && (
          <div style={{
            padding: '8px 12px', borderRadius: 6, fontSize: 12, marginBottom: 16,
            background: message.type === 'error' ? '#fde8e8' : '#e8f5ed',
            color: message.type === 'error' ? '#c0392b' : '#1e7a4a',
          }}>
            {message.text}
          </div>
        )}

        <button
          onClick={handleSave}
          disabled={saving || !isValid}
          style={{
            padding: '9px 20px', borderRadius: 6, fontSize: 13, fontWeight: 600,
            border: 'none', cursor: saving || !isValid ? 'not-allowed' : 'pointer',
            background: !isValid ? '#cbd5e1' : '#1e2a4a', color: '#ffffff',
          }}
        >
          {saving ? '저장 중...' : '저장'}
        </button>
      </PanelCard>
    </div>
  );
}
