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
      setMessage({ type: 'error', text: '의심 기준은 위험 기준보다 낮아야 하며 0~100 사이여야 합니다.' });
      return;
    }

    setSaving(true);
    setMessage(null);
    try {
      await updateDetectionThreshold(highThreshold, mediumThreshold);
      setMessage({ type: 'success', text: '탐지 임계값이 저장되었습니다.' });
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
    <div className="page-content" style={{ maxWidth: 720 }}>
      <PanelCard title="탐지 임계값 설정">
        <p style={{ fontSize: 12, color: '#64748b', marginTop: 0, marginBottom: 18, lineHeight: 1.7 }}>
          이미지 첨부파일의 스테가노그래피 탐지 확률에 따라 위험 등급을 나누는 기준값입니다.
          탐지된 이미지는 차단이 아니라 CDR 무해화 후 전달되며, 실행 파일이나 위장 확장자처럼
          악성 가능성이 높은 첨부파일만 정책 엔진에서 격리/대체 처리됩니다.
        </p>

        <div style={{
          padding: '10px 12px',
          borderRadius: 8,
          background: '#f8fafc',
          border: '1px solid #e2e8f0',
          color: '#475569',
          fontSize: 12,
          lineHeight: 1.7,
          marginBottom: 24,
        }}>
          <strong style={{ color: '#1e2a4a' }}>처리 기준</strong><br />
          정상: 위험 로그 없이 전달<br />
          의심/위험 이미지: CDR 무해화 후 전달 및 관제 로그 기록<br />
          정책 위반 파일: 원본 격리 후 안전 안내 파일로 대체
        </div>

        <div style={{ marginBottom: 28 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
            <label style={{ fontSize: 13, fontWeight: 700, color: '#e05c5c' }}>위험(HIGH) 탐지 기준</label>
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
            탐지 확률이 이 값 이상이면 위험도 HIGH로 분류하고 CDR 무해화 대상으로 기록합니다.
          </p>
        </div>

        <div style={{ marginBottom: 28 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
            <label style={{ fontSize: 13, fontWeight: 700, color: '#d4a23a' }}>의심(MEDIUM) 탐지 기준</label>
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
            탐지 확률이 이 값 이상이면 위험도 MEDIUM으로 분류합니다. HIGH 기준보다 낮아야 합니다.
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
            padding: '9px 20px', borderRadius: 6, fontSize: 13, fontWeight: 700,
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
