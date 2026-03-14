from src.links import generate_short_code
from src.auth import get_password_hash, verify_password

def test_generate_short_code():
    # проверяем генерацию случайного кода
    code1 = generate_short_code()
    code2 = generate_short_code(8)
    
    assert len(code1) == 6
    assert len(code2) == 8
    assert code1 != code2

def test_password_hashing():
    # проверяем хэширование и сверку паролей
    password = "super_secret_password"
    hashed = get_password_hash(password)
    
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrong_password", hashed) is False