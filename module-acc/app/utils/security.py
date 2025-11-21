from passlib.context import CryptContext

# Konfigurasi password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Meng-hash password untuk disimpan di database"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Memverifikasi password dengan hash yang disimpan"""
    return pwd_context.verify(plain_password, hashed_password)
