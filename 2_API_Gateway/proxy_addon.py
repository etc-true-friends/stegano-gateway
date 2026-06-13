"""
/etc/friends mitmproxy 인라인 트래픽 제어 애드온 
"""
import os
import re
import base64
import requests
from mitmproxy import http

API_URL = os.getenv("API_URL", "http://localhost:8000/scan")
IMAGE_MIMES = {"image/png", "image/jpeg", "image/jpg"}
ARCHIVE_MIMES = {
    "application/zip",
    "application/x-zip-compressed",
}

SCAN_MIMES = IMAGE_MIMES | ARCHIVE_MIMES
# 500 에러 방지용 256x256 픽셀 정상 PNG 이미지 바이너리 (Base64)
MOCK_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAQAAAAEACAIAAADTED8xAAACv0lEQVR4nO3TMQEAIAzAsIH/C3e4QQZHEwV9uuaegar9OwB+"
    "MgBpBiDNAKQZgDQDkGYA0gxAmgFIMwBpBiDNAKQZgDQDkGYA0gxAmgFIMwBpBiDNAKQZgDQDkGYA0gxAmgFIMwBpBiDNAKQZ"
    "gDQDkGYA0gxAmgFIMwBpBiDNAKQZgDQDkGYA0gxAmgFIMwBpBiDNAKQZgDQDkGYA0gxAmgFIMwBpBiDNAKQZgDQDkGYA0gxA"
    "mgFIMwBpBiDNAKQZgDQDkGYA0gxAmgFIMwBpBiDNAKQZgDQDkGYA0gxAmgFIMwBpBiDNAKQZgDQDkGYA0gxAmgFIMwBpBiDN"
    "AKQZgDQDkGYA0gxAmgFIMwBpBiDNAKQZgDQDkGYA0gxAmgFIMwBpBiDNAKQZgDQDkGYA0gxAmgFIMwBpBiDNAKQZgDQDkGYA"
    "0gxAmgFIMwBpBiDNAKQZgDQDkGYA0gxAmgFIMwBpBiDNAKQZgDQDkGYA0gxAmgFIMwBpBiDNAKQZgDQDkGYA0gxAmgFIMwBp"
    "BiDNAKQZgDQDkGYA0gxAmgFIMwBpBiDNAKQZgDQDkGYA0gxAmgFIMwBpBiDNAKQZgDQDkGYA0gxAmgFIMwBpBiDNAKQZgDQD"
    "kGYA0gxAmgFIMwBpBiDNAKQZgDQDkGYA0gxAmgFIMwBpBiDNAKQZgDQDkGYA0gxAmgFIMwBpBiDNAKQZgDQDkGYA0gxAmgFI"
    "MwBpBiDNAKQZgDQDkGYA0gxAmgFIMwBpBiDNAKQZgDQDkGYA0gxAmgFIMwBpBiDNAKQZgDQDkGYA0gxAmgFIMwBpBiDNAKQZ"
    "gDQDkGYA0gxAmgFIMwBpBiDNAKQZgDQDkGYA0gxAmgFIMwBpBiDNAKQZgDQDkGYA0gxAmgFIMwBpBiDNAKQZgDQDkGYA0gxA"
    "mgFIMwBpBiDNAKQZgDQDkGYA0gxAmgFIMwBpBiDNAKQZgDQDkGYA0gxAmgFIMwBpBiDNAKQZgDQDkGYA0gxAmgFIMwBpBiDN"
    "AKQZgDQDkGYA0h7VsgNrD8aOMAAAAABJRU5ErkJggg=="
)
MOCK_PNG = base64.b64decode(MOCK_BASE64)
def guess_upload_meta(raw: bytes, default_name: str = "proxy_stream.bin"):
    """
    mitmproxy에서 받은 raw body를 보고 /scan에 보낼 파일명과 MIME을 결정한다.
    Content-Type이 애매한 application/octet-stream이어도 ZIP/PNG/JPEG 시그니처로 구분한다.
    """
    if raw.startswith(b"PK\x03\x04") or raw.startswith(b"PK\x05\x06") or raw.startswith(b"PK\x07\x08"):
        return "archive_payload.zip", "application/zip"

    if raw.startswith(b"\x89PNG"):
        return "image_payload.png", "image/png"

    if raw.startswith(b"\xff\xd8\xff"):
        return "image_payload.jpg", "image/jpeg"

    return default_name, "application/octet-stream"

class SteganoCDRAddon:
    def __init__(self):
        print("[+] /etc/friends Stegano CDR mitmproxy Addon Loaded.")

    def is_internal(self, ip: str) -> bool:
        if not ip:
            return False
        return (
            ip.startswith("127.") or
            ip.startswith("192.168.") or
            ip.startswith("10.") or
            ip.startswith("172.") or
            ip == "::1"
        )

    def request(self, flow: http.HTTPFlow):
        host = flow.request.pretty_host
        path = flow.request.path

        # ─────────────────────────────────────────────────
        # [모의 망연계 포털] 전용 인터셉트 통제 로직
        # ─────────────────────────────────────────────────
        if "external-mail-server.local" in host:
            
            # [CASE 1] OUTBOUND: 파일 반출 (POST)
            if "/api/v1/upload" in path and flow.request.method == "POST":
                print("\n" + "="*60)
                print("[*] 모의 포털 [OUTBOUND] 반출 트래픽 감지!")
                
                raw_file = None
                content_type = flow.request.headers.get("content-type", "")
                boundary_match = re.search(r"boundary=(.+)", content_type, re.IGNORECASE)
                
                # 정밀 바이너리 파서: WebKit 따옴표 예외 처리 반영
                if boundary_match:
                    boundary = boundary_match.group(1).strip().strip('"').encode('utf-8')
                    parts = flow.request.content.split(b"--" + boundary)
                    for part in parts:
                        if b'name="file"' in part:
                            if b"\r\n\r\n" in part:
                                _, file_bytes = part.split(b"\r\n\r\n", 1)
                                if file_bytes.endswith(b"\r\n"):
                                    file_bytes = file_bytes[:-2]
                                if file_bytes.endswith(b"--\r\n"):
                                    file_bytes = file_bytes[:-4]
                                elif file_bytes.endswith(b"--"):
                                    file_bytes = file_bytes[:-2]
                                raw_file = file_bytes
                                break
                
                if not raw_file:
                    print("[!] 바이너리 파싱 폴백 -> 전체 Content 참조")
                    raw_file = flow.request.content

                print(f"[+] API 호출 대상: {API_URL}")
                print(f"[+] 전송 파일 크기: {len(raw_file)} bytes")

                try:
                    upload_name, upload_mime = guess_upload_meta(raw_file, "outbound_payload.bin")
                    response = requests.post(
                        API_URL,
                        files={"file": (upload_name, raw_file, upload_mime)},
                        data={"direction": "OUTBOUND"},
                        timeout=10.0,
                        proxies={"http": None, "https": None}
                    )
                    
                    print(f"[+] API 응답 상태 코드: {response.status_code}")
                    print(f"[+] API 판정 결과 (Verdict): {response.headers.get('X-Gateway-Verdict', '없음')}")
                    
                    headers = {k: v for k, v in response.headers.items() if k.lower().startswith("x-gateway-") or k.lower() == "content-type"}
                    headers["Access-Control-Allow-Origin"] = "*"
                    headers["Access-Control-Expose-Headers"] = "*"
                    
                    flow.response = http.Response.make(response.status_code, response.content, headers)
                    print("[+] 브라우저 모의 포털로 데이터 릴레이 완료.")
                    print("="*60 + "\n")
                except Exception as e:
                    print(f"[ERROR] OUTBOUND API 연동 실패: {e}")
                    flow.response = http.Response.make(502, b"Gateway Error", {"Content-Type": "text/plain"})
                    print("="*60 + "\n")
                return

            # [CASE 2] INBOUND: 외부 파일 수신/다운로드 (GET)
            elif "/api/v1/download" in path and flow.request.method == "GET":
                print("\n" + "="*60)
                print("[*] 모의 포털 [INBOUND] 반입 트래픽 감지!")
                print(f"[+] API 호출 대상: {API_URL}")
                print(f"[+] 전송 파일 크기 (정렬 규격): {len(MOCK_PNG)} bytes")
                
                try:
                    response = requests.post(
                        API_URL,
                        files={"file": ("inbound_intrusion_attempt.png", MOCK_PNG, "image/png")},
                        data={"direction": "INBOUND"},
                        timeout=10.0,
                        proxies={"http": None, "https": None}
                    )
                    
                    print(f"[+] API 응답 상태 코드: {response.status_code}")
                    print(f"[+] API 판정 결과 (Verdict): {response.headers.get('X-Gateway-Verdict', '없음')}")
                    
                    headers = {k: v for k, v in response.headers.items() if k.lower().startswith("x-gateway-") or k.lower() == "content-type"}
                    headers["Access-Control-Allow-Origin"] = "*"
                    headers["Access-Control-Expose-Headers"] = "*"
                    
                    flow.response = http.Response.make(response.status_code, response.content, headers)
                    print("[+] 브라우저 모의 포털로 데이터 릴레이 완료.")
                    print("="*60 + "\n")
                except Exception as e:
                    print(f"[ERROR] INBOUND API 연동 실패: {e}")
                    flow.response = http.Response.make(502, b"Gateway Error", {"Content-Type": "text/plain"})
                    print("="*60 + "\n")
                return

        # ─────────────────────────────────────────────────
        # [일반 웹 서핑] 관제 통제 규칙 (기존 유지)
        # ─────────────────────────────────────────────────
        content_type = flow.request.headers.get("content-type", "").lower()
        client_ip = flow.client_conn.peername[0] if flow.client_conn.peername else "127.0.0.1"
        if self.is_internal(client_ip) and any(mime in content_type for mime in SCAN_MIMES):
            self._process(flow, direction="OUTBOUND")

    def response(self, flow: http.HTTPFlow):
        if not flow.response or "external-mail-server.local" in flow.request.pretty_host:
            return
        content_type = flow.response.headers.get("content-type", "").lower()
        if any(mime in content_type for mime in SCAN_MIMES):
            self._process(flow, direction="INBOUND")

    def _process(self, flow: http.HTTPFlow, direction: str):
        try:
            raw = flow.request.content if direction == "OUTBOUND" else flow.response.content
            if not raw: return
            upload_name, upload_mime = guess_upload_meta(raw, "proxy_stream.bin")

            response = requests.post(
                API_URL,
                files={"file": (upload_name, raw, upload_mime)},
                data={"direction": direction},
                timeout=5.0,
                proxies={"http": None, "https": None}
            )

            if response.status_code == 200:
                if direction == "OUTBOUND": flow.request.content = response.content
                else: flow.response.content = response.content

                for k, v in response.headers.items():
                    if k.lower().startswith("x-gateway-"):
                        if direction == "OUTBOUND": flow.request.headers[k] = v
                        else: flow.response.headers[k] = v
            elif response.status_code in (400, 403):
                html = "<html><body><h1 style='color:red;'>403 Forbidden</h1></body></html>".encode('utf-8')
                flow.response = http.Response.make(403, html, {"Content-Type": "text/html"})
        except Exception as e:
            pass

addons = [SteganoCDRAddon()]