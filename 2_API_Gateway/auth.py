"""
직원(employee) 로그인 API — SQLite 기반 인증 뼈대
"""

import hashlib
import secrets
import sqlite3
import uuid
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/auth", tags=["auth"])

DB_PATH: Optional[str] = None

KST = ZoneInfo("Asia/Seoul")


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1)


class LoginUser(BaseModel):
    id: int
    email: str
    username: str


class LoginResponse(BaseModel):
    success: bool
    token: str
    user: LoginUser


def configure(db_path: str) -> None:
    global DB_PATH
    DB_PATH = db_path


def _conn() -> sqlite3.Connection:
    if not DB_PATH:
        raise RuntimeError("auth DB_PATH is not configured")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    if not stored:
        return False
    try:
        salt, digest = stored.split("$", 1)
    except ValueError:
        return secrets.compare_digest(password, stored)
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest() == digest


def init_employee_table() -> None:
    conn = _conn()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employee (
            id INTEGER PRIMARY KEY,
            username VARCHAR(64),
            password VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            b_deleted CHAR(1) DEFAULT 'N'
        )
    """)
    columns = {row["name"] for row in cursor.execute("PRAGMA table_info(employee)").fetchall()}
    if "email" not in columns:
        cursor.execute("ALTER TABLE employee ADD COLUMN email VARCHAR(255)")
    cursor.execute(
        """
        UPDATE employee
        SET username = 'admin'
        WHERE email = 'admin@gmail.com'
          AND username = 'admin@gmail.com'
          AND b_deleted = 'N'
        """
    )
    conn.commit()
    conn.close()


def seed_default_employee() -> None:
    """테스트용 기본 계정은 직원 테이블이 비어 있을 때만 생성한다."""
    conn = _conn()
    cursor = conn.cursor()

    # 계정이 아예 없으면 기본 admin 생성
    cursor.execute("SELECT COUNT(*) FROM employee WHERE b_deleted = 'N'")
    if cursor.fetchone()[0] == 0:
        now = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            """
            INSERT INTO employee (id, email, username, password, created_at, b_deleted)
            VALUES (?, ?, ?, ?, ?, 'N')
            """,
            (1, "admin@gmail.com", 'admin', hash_password("admin123"), now),
        )
        print("[+] Auth: 기본 계정 생성 (admin@gmail.com / admin123)")

        cursor.execute(
            """
            INSERT INTO employee (id, email, username, password, created_at, b_deleted)
            VALUES (?, ?, ?, ?, ?, 'N')
            """,
            (2, "test@gmail.com", 'test', hash_password("test123"), now),
        )
        print("[+] Auth: 기본 계정 생성 (test@gmail.com / test123)")

    conn.commit()
    conn.close()


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest) -> LoginResponse:
    conn = _conn()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, email, username, password
        FROM employee
        WHERE email = ? AND b_deleted = 'N'
        LIMIT 1
        """,
        (body.email.strip(),),
    )
    row = cursor.fetchone()
    conn.close()

    if row is None or not verify_password(body.password, row["password"]):
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다.")

    token = str(uuid.uuid4())
    return LoginResponse(
        success=True,
        token=token,
        user=LoginUser(id=row["id"], email=row["email"], username=row["username"]),
    )


@router.get("/me")
def me(email: str) -> dict:
    """토큰 검증 전 단계 — email로 직원 존재 여부 확인 (뼈대)"""
    conn = _conn()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, email, username, created_at
        FROM employee
        WHERE email = ? AND b_deleted = 'N'
        LIMIT 1
        """,
        (email.strip(),),
    )
    row = cursor.fetchone()
    conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    return {
        "id": row["id"],
        "email": row["email"],
        "username": row["username"],
        "created_at": row["created_at"],
    }
