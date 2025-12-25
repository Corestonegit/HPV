import sys
sys.path.insert(0, '.')

from auth import get_user, authenticate_user, verify_password, get_password_hash

# Тестируем вход для последнего зарегистрированного пользователя
username = 'sknd'
password = 'test123'  # Замените на реальный пароль

print(f"Тестирование входа для пользователя: {username}")
user = get_user(username)
if user:
    print(f"Пользователь найден: {user.username}")
    print(f"Активен: {user.is_active}")
    print(f"Есть пароль: {bool(user.hashed_password)}")
    print(f"Хеш пароля: {user.hashed_password[:50]}...")
    
    # Тестируем проверку пароля
    print(f"\nТестирование пароля '{password}':")
    result = verify_password(password, user.hashed_password)
    print(f"Результат проверки: {result}")
    
    # Тестируем полную аутентификацию
    print(f"\nТестирование authenticate_user:")
    auth_result = authenticate_user(username, password)
    print(f"Результат: {auth_result is not None}")
    if auth_result:
        print(f"Аутентифицирован как: {auth_result.username}")
else:
    print(f"Пользователь {username} не найден")

