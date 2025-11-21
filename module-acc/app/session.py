from fastapi import Request, HTTPException

SESSION_COOKIE = "acc_session"  # Nama cookie session

def create_session(response, user_id: int):
    """Membuat session cookie setelah login berhasil"""
    response.set_cookie(
        key=SESSION_COOKIE,
        value=str(user_id),
        httponly=True,      # Anti XSS
        samesite="lax",     # Security
        max_age=60*60*24    # 24 jam
    )

def destroy_session(response):
    """Menghapus session cookie saat logout"""
    response.delete_cookie(SESSION_COOKIE)

def require_login(request: Request):
    """Dependency untuk memproteksi routes - wajib login"""
    user_id = request.cookies.get(SESSION_COOKIE)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not logged in")
    return int(user_id)