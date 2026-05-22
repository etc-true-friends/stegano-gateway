"""
/etc/friends mitmproxy 인라인 트래픽 제어 애드온 (최종 완성본)
- 이미지 트래픽 자동 감지 및 가로채기
- 고도화된 api.py /scan API 연동 규격 준수
- 클라이언트 IP 주소 기반 INBOUND / OUTBOUND 실시간 자동 판별
- MIME 검증 실패(400) 시 보안팀 커스텀 403 Forbidden 대피 페이지 사출
"""

import requests
from mitmproxy import http

# API 서버 주소 및 검사 대상 확장자 정의
API_URL = "http://127.0.0.1:8000/scan"
IMAGE_MIMES = {"image/png", "image/jpeg", "image/jpg"}


class SteganoCDRAddon:
    def __init__(self):
        print("[+] /etc/friends Stegano CDR mitmproxy Addon Loaded.")

    def is_internal(self, ip: str) -> bool:
        """클라이언트 IP가 사설 및 루프백 대역폭(내부망)에 속하는지 검증"""
        if not ip:
            return False
        return (
            ip.startswith("127.") or 
            ip.startswith("192.168.") or 
            ip.startswith("10.") or
            ip == "::1"  # IPv6 루프백 대응
        )

    def request(self, flow: http.HTTPFlow):
        """
        [OUTBOUND 통제] 내부망 사용자가 외부로 이미지 업로드(반출) 시 가로채기
        """
        # 클라이언트 IP 추출
        client_ip = flow.client_conn.peername[0] if flow.client_conn.peername else "127.0.0.1"
        content_type = flow.request.headers.get("content-type", "").lower()

        # 내부망 유저가 이미지를 반출하려는 조건 부합 시 작동
        if self.is_internal(client_ip) and any(mime in content_type for mime in IMAGE_MIMES):
            print(f"[*] Outbound 데이터 전송 탐지 (Origin: {client_ip}) -> 게이트웨이 검사 시동")
            self._process(flow, direction="OUTBOUND")

    def response(self, flow: http.HTTPFlow):
        """
        [INBOUND 통제] 외부에서 내부망 사용자로 이미지 다운로드/렌더링(반입) 시 가로채기
        """
        if not flow.response:
            return

        content_type = flow.response.headers.get("content-type", "").lower()

        # 외부에서 유입되는 트래픽 중 이미지 소스가 감지되면 무해화 파이프라인 가동
        if any(mime in content_type for mime in IMAGE_MIMES):
            self._process(flow, direction="INBOUND")

    def _process(self, flow: http.HTTPFlow, direction: str):
        """
        양방향 공통 처리 코어 파이프라인
        """
        try:
            # 1. 방향성에 따른 이미지 스트림 원본 자산 추출
            if direction == "OUTBOUND":
                raw = flow.request.content
                filename = "outbound_leak_attempt.png"
            else:
                raw = flow.response.content
                filename = "inbound_intrusion_attempt.png"

            if not raw:
                return

            # 2. 고도화된 api.py 규격에 맞춰 multipart/form-data 요청 전송
            response = requests.post(
                API_URL,
                files={"file": (filename, raw, "image/png")},
                data={"direction": direction},  # 수정한 api.py가 수신하는 Form 파라미터
                timeout=5.0                     # 인라인 가용성을 위한 5초 타임아웃
            )

            # 3. [정상 처리 완료] 무해화된 바이너리로 교체 및 메타데이터 헤더 주입
            if response.status_code == 200:
                sanitized = response.content

                # 백엔드가 응답 헤더에 심어준 탐지 및 통계 지표 추출
                verdict = response.headers.get("X-Gateway-Verdict", "UNKNOWN")
                risk = response.headers.get("X-Gateway-Risk-Level", "UNKNOWN")
                prob = response.headers.get("X-Gateway-Stego-Prob", "0.0%")

                if direction == "OUTBOUND":
                    flow.request.content = sanitized
                    # 아웃바운드는 요청 헤더를 변조하여 전송
                    flow.request.headers["X-Gateway-Verdict"] = verdict
                    flow.request.headers["X-Gateway-Risk-Level"] = risk
                else:
                    flow.response.content = sanitized
                    # 인바운드는 브라우저가 인지하도록 응답 헤더를 변조
                    flow.response.headers["X-Gateway-Verdict"] = verdict
                    flow.response.headers["X-Gateway-Risk-Level"] = risk
                    flow.response.headers["X-Gateway-Stego-Prob"] = prob

                print(f"[{direction}] 처리 완료 | 결과: {verdict} ({prob}) | 위험도: {risk}")

            # 4. [정책 위함 발견] 확장자 위장 등 MIME 가드 위반 시 물리적 강제 차단
            elif response.status_code == 400:
                print(f"[-] [{direction}] 보안 정책 위반(MIME 차단) 조건 발동 -> 차단 스크립트 강제 사출")
                
                # 보안 관제용 HTML 403 Forbidden Response 동적 주입 (양방향 동일 적용)
                flow.response = http.Response.make(
                    403,
                    (
                        b"<html><head><meta charset='utf-8'>"
                        b"<title>403 Forbidden - Security Blocked</title></head>"
                        b"<body style='font-family:sans-serif; text-align:center; padding-top:100px; background-color:#fafafa;'>"
                        b"<div style='display:inline-block; border:2px solid #dc3545; padding:40px; background:#fff; border-radius:8px; box-shadow:0 4px 6px rgba(0,0,0,0.1);'>"
                        b"<h1 style='color:#dc3545; margin-top:0;'>[!] Access Denied (403 Forbidden)</h1>"
                        b"<p style='font-size:16px; color:#333; font-weight:bold;'>보안 정책 위반 파일이 탐지되어 게이트웨이에서 연결을 강제 통제했습니다.</p>"
                        b"<p style='color:#666; font-size:14px;'>대상 자산은 격리(Quarantine) 조치되었으며, 감사 로그에 영구 기록되었습니다.</p>"
                        b"<hr style='border:0; border-top:1px solid #eee; margin:20px 0;'>"
                        b"<p style='font-size:12px; color:#999;'>/etc/friends Integrated Security Pipeline Enterprise v1.0</p>"
                        b"</div></body></html>"
                    ),
                    {"Content-Type": "text/html"}
                )

        except requests.exceptions.RequestException as e:
            # 백엔드 가동 불능 시 전체 네트워크 다운을 막는 Fail-Open 전략 이식
            print(f"[ERROR] [Fail-Open 활성화] 게이트웨이 코어 연동 실패: {e}")


# mitmproxy 애드온 등록
addons = [SteganoCDRAddon()]