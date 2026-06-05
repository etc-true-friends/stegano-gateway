import { useState, useRef } from 'react';
import { Upload, ScanLine } from 'lucide-react';
import { scanFile } from '../../api/gateway';

const RISK_COLOR = { HIGH: '#ff4444', MEDIUM: '#ffaa00', LOW: '#00cc66' };
const RISK_DOT = { HIGH: '🔴', MEDIUM: '🟡', LOW: '🟢' };

export default function FileScanPanel() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState(null);
  const inputRef = useRef();

  function handleFile(f) {
    if (!f) return;
    setFile(f);
    setResult(null);
    setError(null);
    const reader = new FileReader();
    reader.onload = e => setPreview(e.target.result);
    reader.readAsDataURL(f);
  }

  function onDrop(e) {
    e.preventDefault();
    handleFile(e.dataTransfer.files[0]);
  }

  async function handleScan() {
    if (!file) return;
    setScanning(true);
    setError(null);
    try {
      const data = await scanFile(file);
      setResult(data);
    } catch (e) {
      setError(e.message || '스캔 실패');
    } finally {
      setScanning(false);
    }
  }

  const detection = result?.pipeline?.step1_detection;
  const sanitization = result?.pipeline?.step2_sanitization;
  const quarantine = result?.pipeline?.step3_quarantine;
  const prob = detection ? parseFloat(String(detection.stego_probability).replace('%', '')) : null;
  const level = detection?.risk_level;
  const verdict = detection?.verdict;

  return (
    <div className="scan-panel">
      <div className="section-label">// FILE SCAN — 파일 업로드 및 탐지</div>

      <div className="scan-layout">
        {/* 업로드 영역 */}
        <div className="scan-left">
          <div
            className="dropzone"
            onDrop={onDrop}
            onDragOver={e => e.preventDefault()}
            onClick={() => inputRef.current.click()}
          >
            {preview ? (
              <img src={preview} alt="preview" className="preview-img" />
            ) : (
              <div className="dropzone-hint">
                <Upload size={32} className="drop-icon" />
                <div>이미지를 드래그하거나 클릭하여 선택</div>
                <div className="drop-types">PNG · JPG · BMP · WEBP</div>
              </div>
            )}
          </div>
          <input
            ref={inputRef}
            type="file"
            accept=".png,.jpg,.jpeg,.bmp,.webp"
            style={{ display: 'none' }}
            onChange={e => handleFile(e.target.files[0])}
          />
          {file && (
            <div className="file-meta">
              FILE · {file.name}<br />
              SIZE · {Math.round(file.size / 1024)} KB
            </div>
          )}
        </div>

        {/* 결과 영역 */}
        <div className="scan-right">
          <div className="section-label">// ANALYSIS</div>

          <button
            className="scan-btn"
            onClick={handleScan}
            disabled={!file || scanning}
          >
            <ScanLine size={14} />
            {scanning ? 'SCANNING...' : 'SCAN & SANITIZE'}
          </button>

          {error && <div className="scan-error">ERROR: {error}</div>}

          {detection && (
            <div className={`result-box ${verdict === 'SUSPICIOUS' ? 'result-suspicious' : 'result-clean'}`}>
              <div className="result-prob" style={{ color: RISK_COLOR[level] }}>
                {prob?.toFixed(1)}%
              </div>
              <div className="result-verdict" style={{ color: RISK_COLOR[level] }}>
                {RISK_DOT[level]} {level} RISK · {verdict}
              </div>
            </div>
          )}

          {sanitization && (
            <div className="result-box cdr-box">
              <div className="section-label">// CDR SANITIZATION</div>
              {(sanitization.steps || []).map((step, i) => (
                <div key={i} className="cdr-step">✓ {step}</div>
              ))}
              <div className="cdr-meta">
                PIXEL DIFF · {sanitization.pixel_diff ?? '-'}
                &nbsp;&nbsp;
                QUARANTINE · {quarantine?.quarantined ? 'YES' : 'NO'}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
