from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from enum import Enum
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import json
import os

# Настройки для JWT
SECRET_KEY = "your-secret-key-change-in-production"  # В продакшене использовать переменную окружения
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 * 24 * 60  # 30 дней

# Настройки для хеширования паролей
# Используем pbkdf2_sha256 как основную схему, так как она более надежна и не имеет проблем совместимости
pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")

# Файл для хранения пользователей
USERS_FILE = os.path.join(os.path.dirname(__file__), "users.json")

# Безопасность для JWT токенов
security = HTTPBearer()

# Роли пользователей
class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"

# Модели Pydantic
class User(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    hashed_password: str
    role: UserRole = UserRole.USER
    is_active: bool = True
    created_at: Optional[str] = None

class UserCreate(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    password: str
    role: UserRole = UserRole.USER

class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None

class UserResponse(BaseModel):
    """Модель пользователя для ответа (без пароля)"""
    username: str
    email: Optional[str] = None
    role: str = "user"
    is_active: bool = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    roles: Optional[UserRole] = None

# Функции для работы с паролями
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# Функции для работы с JWT
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

# Функции для работы с файлом пользователей
def load_users() -> dict:
    """Загрузить всех пользователей из файла"""
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_users(users: dict):
    """Сохранить пользователей в файл"""
    try:
        # Создаем директорию, если её нет
        os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка при сохранении пользователей: {e}")
        raise

def get_user(username: str) -> Optional[User]:
    """Получить пользователя по имени"""
    users = load_users()
    user_data = users.get(username)
    if user_data:
        # Преобразуем role в UserRole enum если нужно
        role = user_data.get("role", UserRole.USER)
        if isinstance(role, str):
            role = UserRole.USER if role == "user" else UserRole.ADMIN
        return User(
            username=user_data.get("username", username),
            email=user_data.get("email"),
            full_name=user_data.get("full_name"),
            hashed_password=user_data.get("hashed_password", ""),
            role=role,
            is_active=user_data.get("is_active", True),
            created_at=user_data.get("created_at")
        )
    return None

def create_user(user_data: UserCreate) -> User:
    """Создать нового пользователя"""
    try:
        users = load_users()
        
        # Проверяем, что пользователь не существует
        if user_data.username in users:
            raise ValueError("Пользователь с таким именем уже существует")
        
        # Проверяем email, если указан
        if user_data.email:
            for username, user in users.items():
                if user.get("email") == user_data.email:
                    raise ValueError("Пользователь с таким email уже существует")
        
        # Хешируем пароль
        try:
            hashed_password = get_password_hash(user_data.password)
        except Exception as e:
            print(f"Ошибка при хешировании пароля: {e}")
            raise ValueError(f"Ошибка при создании пользователя: {str(e)}")
        
        # Создаем пользователя
        user = User(
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            hashed_password=hashed_password,
            role=user_data.role,
            is_active=True,
            created_at=datetime.utcnow().isoformat()
        )
        
        users[user.username] = {
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "hashed_password": user.hashed_password,
            "role": user.role.value if isinstance(user.role, UserRole) else user.role,
            "is_active": user.is_active,
            "created_at": user.created_at
        }
        save_users(users)
        return user
    except ValueError:
        raise
    except Exception as e:
        print(f"Неожиданная ошибка при создании пользователя: {e}")
        import traceback
        traceback.print_exc()
        raise ValueError(f"Ошибка при создании пользователя: {str(e)}")

def update_user(user: User) -> User:
    """Обновить пользователя"""
    users = load_users()
    
    if user.username not in users:
        raise ValueError("Пользователь не найден")
    
    user_data = users[user.username]
    
    # Обновляем поля
    user_data["email"] = user.email
    user_data["full_name"] = user.full_name
    user_data["role"] = user.role.value if isinstance(user.role, UserRole) else user.role
    user_data["is_active"] = user.is_active
    user_data["hashed_password"] = user.hashed_password
    
    users[user.username] = user_data
    save_users(users)
    
    # Возвращаем пользователя с правильным типом роли
    role = user_data.get("role", UserRole.USER)
    if isinstance(role, str):
        role = UserRole.USER if role == "user" else UserRole.ADMIN
    return User(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        hashed_password=user.hashed_password,
        role=role,
        is_active=user.is_active,
        created_at=user_data.get("created_at")
    )

def authenticate_user(username: str, password: str) -> Optional[User]:
    """Аутентифицировать пользователя"""
    try:
        print(f"[AUTH] Попытка входа для пользователя: {username}")
        user = get_user(username)
        if not user:
            print(f"[AUTH] Пользователь {username} не найден")
            return None
        if not user.is_active:
            print(f"[AUTH] Пользователь {username} заблокирован")
            return None
        if not user.hashed_password:
            print(f"[AUTH] У пользователя {username} нет пароля")
            return None
        print(f"[AUTH] Проверка пароля для пользователя {username}")
        print(f"[AUTH] Хеш пароля: {user.hashed_password[:50]}...")
        password_valid = verify_password(password, user.hashed_password)
        print(f"[AUTH] Результат проверки пароля: {password_valid}")
        if not password_valid:
            print(f"[AUTH] Неверный пароль для пользователя {username}")
            return None
        print(f"[AUTH] Успешная аутентификация пользователя {username}")
        return user
    except Exception as e:
        print(f"[AUTH] Ошибка при аутентификации пользователя {username}: {e}")
        import traceback
        traceback.print_exc()
        return None

def init_default_admin():
    """Инициализировать администратора по умолчанию"""
    try:
        users = load_users()
        
        # Проверяем, есть ли уже администратор
        has_admin = any(
            user.get("role") == UserRole.ADMIN.value or user.get("role") == "admin" 
            for user in users.values()
        )
        
        if not has_admin:
            admin = UserCreate(
                username="admin",
                email="admin@example.com",
                password="Admin@2024!Secure#Pass",  # Сложный пароль
                role=UserRole.ADMIN
            )
            create_user(admin)
            print(f"[INFO] Создан администратор по умолчанию: username=admin, password=Admin@2024!Secure#Pass")
    except Exception as e:
        # Если не удалось создать администратора, просто логируем ошибку
        # Это не должно останавливать запуск сервера
        print(f"[WARNING] Не удалось создать администратора по умолчанию: {e}")
        print(f"[INFO] Вы можете создать администратора вручную через API /api/users/register")

# Функции для dependency injection
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Получить текущего пользователя из токена"""
    try:
        token = credentials.credentials
        print(f"[AUTH] Проверка токена: {token[:20]}...")
        payload = decode_access_token(token)
        if payload is None:
            print("[AUTH] Токен не декодирован")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Недействительный токен",
                headers={"WWW-Authenticate": "Bearer"},
            )
        username: str = payload.get("sub")
        print(f"[AUTH] Username из токена: {username}")
        if username is None:
            print("[AUTH] Username не найден в токене")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Недействительный токен",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user = get_user(username)
        if user is None:
            print(f"[AUTH] Пользователь {username} не найден в базе")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Пользователь не найден",
                headers={"WWW-Authenticate": "Bearer"},
            )
        print(f"[AUTH] Пользователь {username} успешно аутентифицирован")
        return user
    except HTTPException:
        raise
    except Exception as e:
        print(f"[AUTH] Ошибка при проверке токена: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ошибка проверки токена",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Получить активного пользователя"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Пользователь заблокирован"
        )
    return current_user

async def get_current_active_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    """Проверить, что текущий пользователь - активный администратор"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав доступа"
        )
    return current_user

# Инициализация при импорте (с обработкой ошибок)
try:
    init_default_admin()
except Exception as e:
    print(f"[WARNING] Ошибка при инициализации администратора: {e}")
    print(f"[INFO] Сервер продолжит работу, но администратор не был создан автоматически")

