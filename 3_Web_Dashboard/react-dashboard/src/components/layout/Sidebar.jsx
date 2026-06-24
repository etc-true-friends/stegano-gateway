import { LayoutDashboard, Monitor, FileSearch, BarChart2, Shield, Server, ChevronRight } from 'lucide-react';
import mascot from '../../assets/mascot.png';

const MENU_GROUPS = [
  {
    label: '실시간 모니터링',
    icon: Monitor,
    items: [
      { label: '위협 현황', page: null },
      { label: 'CDR 처리 현황', page: null },
    ]
  },
  {
    label: '로그 조회',
    icon: FileSearch,
    items: [
      { label: '감사 로그', page: 'audit' },
      { label: '탐지 이력', page: null },
      { label: '차단 이력', page: null },
    ]
  },
  {
    label: '보고서',
    icon: BarChart2,
    items: [
      { label: '일별 탐지 통계', page: 'daily-stats' },
      { label: '파일 유형별 분석', page: 'file-type' },
      { label: '위험도 추이', page: null },
    ]
  },
  {
    label: '정책 관리',
    icon: Shield,
    items: [
      { label: '탐지 임계값 설정', page: null },
      { label: '화이트리스트 관리', page: null },
      { label: '알림 설정', page: null },
    ]
  },
  {
    label: '시스템',
    icon: Server,
    items: [
      { label: 'API 상태', page: null },
      { label: 'AI 모델 정보', page: null },
      { label: '연동 현황', page: null },
    ]
  },
];

export default function Sidebar({ activePage, onNavigate }) {
  return (
    <aside className="sidebar">

      {/* 대시보드 메뉴 */}
      <nav className="sidebar-nav" style={{ marginTop: 8 }}>
        <button
          className={`nav-item ${activePage === 'dashboard' ? 'active' : ''}`}
          onClick={() => onNavigate('dashboard')}
        >
          <LayoutDashboard size={14} />
          대시보드
        </button>
      </nav>

      {/* 메뉴 그룹 */}
      {MENU_GROUPS.map(group => {
        const Icon = group.icon;
        return (
          <div key={group.label} className="sidebar-section">
            <div className="section-label" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <Icon size={11} />
              {group.label}
            </div>
            {group.items.map(item => (
              <div
                key={item.label}
                className={`pipeline-step ${activePage === item.page ? 'active' : ''}`}
                style={{ cursor: item.page ? 'pointer' : 'default', paddingLeft: 8, opacity: item.page ? 1 : 0.5, fontWeight: item.page ? 600 : 400 }}
                onClick={() => item.page && onNavigate(item.page)}
              >
                <ChevronRight size={10} />
                {item.label}
              </div>
            ))}
          </div>
        );
      })}
    </aside>
  );
}