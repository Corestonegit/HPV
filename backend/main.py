from fastapi import FastAPI, Query, Body, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordRequestForm
import json
import os
from typing import Optional, List, Dict
from collections import defaultdict
from pydantic import BaseModel
from datetime import timedelta

# Импорты для аутентификации
from auth import (
    User, UserCreate, UserUpdate, UserResponse, Token, TokenData,
    authenticate_user, create_user, get_user, update_user, load_users,
    create_access_token, decode_access_token, UserRole,
    get_current_user, get_current_active_user, get_current_active_admin_user
)

app = FastAPI(
    title="Sales Dashboard API",
    description="API для дашборда с подсказками для менеджеров отдела продаж",
    version="1.0.0"
)


@app.on_event("startup")
async def startup_event():
    """При старте выводим зарегистрированные маршруты"""
    for route in app.routes:
        if hasattr(route, "path") and hasattr(route, "methods"):
            print(f"[ROUTE] {list(route.methods)} {route.path}")

# Настройка CORS для работы с React фронтендом
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002", "http://localhost:3003", "http://localhost:3004", "http://localhost:3005", "http://localhost:3006", "http://localhost:3007", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Маппинг названий тарифов
PLAN_NAMES = {
    "standard": "Стандарт",
    "expert": "Эксперт",
    "optimal": "Оптима",
    "express": "Экспресс",
    "ultra": "Ультра"
}

# Маппинг названий разделов (table_name -> читаемое название)
TABLE_NAME_MAPPING = {
    "gibkost": "Гибкость команды",
    "srochnost": "Срочность",
    "безопасность": "Безопасность",
    "целевой сервис": "Целевой сервис",
    "Бухгалтерия": "Бухгалтерия",
    "Прозрачная отчетность": "Прозрачная отчетность",
    "Конструкторское бюро": "Конструкторское бюро",
    "gisp": "ГИСП",
    "izmeneniya": "Изменения",
    "tpp": "ТПП",
    "podryadchiki": "Подрядчики",
    "Подрядчики": "Подрядчики",
    "kommunikacii": "Коммуникации",
    "Коммуникации": "Коммуникации",
    "podderjka": "Поддержка",
    "Поддержка": "Поддержка"
}

# Список JSON файлов для загрузки
def get_all_json_files() -> list:
    """Получить список всех JSON файлов с данными (динамически)"""
    backend_dir = os.path.dirname(__file__)
    json_files = []
    for filename in os.listdir(backend_dir):
        if filename.endswith('.json') and filename != 'users.json':
            json_files.append(filename)
    return json_files


# Для обратной совместимости - динамический список
JSON_FILES = get_all_json_files()


def load_table_data(filename: str) -> Dict:
    """Загрузить данные из JSON файла таблицы"""
    file_path = os.path.join(os.path.dirname(__file__), filename)
    if not os.path.exists(file_path):
        return None
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_category(cat: str) -> str:
    """Нормализация категорий"""
    if not cat:
        return ""
    cat = cat.strip()
    # Нормализация "Легкость"
    cat = cat.replace("Лёгкость", "Легкость").replace("лёгкость", "легкость")
    cat = cat.replace("Лекость", "Легкость")  # Исправление опечаток
    # Нормализация "Безопасность"
    # Исправляем опечатки и дублирования
    cat = cat.replace("Безопасностьасность", "Безопасность")  # Исправление опечаток
    cat = cat.replace("Безопасность, Безопасность", "Безопасность")  # Убираем дубликаты
    cat = cat.replace("Безопасность,Безопасность", "Безопасность")  # Убираем дубликаты без пробела
    cat = cat.replace("Безопастность", "Безопасность")  # Исправление опечаток
    cat = cat.replace("Безоп", "Безопасность")  # Сокращение
    # Нормализация "Экономия"
    cat = cat.replace("Эконом", "Экономия")  # Сокращение
    # Нормализация "Скорость"
    cat = cat.replace("Сроки", "Скорость")  # Вариант названия
    return cat


def deduplicate_pains(pains_str: str) -> str:
    """Нормализует и удаляет дубликаты из строки болей"""
    if not pains_str:
        return ""
    parts = [normalize_category(p.strip()) for p in pains_str.split(",") if p.strip()]
    # Убираем дубликаты, сохраняя порядок
    seen = set()
    unique = []
    for cat in parts:
        if cat and cat not in seen:
            seen.add(cat)
            unique.append(cat)
    return ", ".join(unique)


def expand_abbreviations(value: str) -> str:
    """Расшифровка сокращений в значениях"""
    if not value or value == "-" or value == "+":
        return value
    
    value = value.strip()
    
    # Расшифровка сокращений с учетом чисел
    import re
    
    # Мин/Макс с числами и "рд" (например: "Мин 10 рд" -> "Минимум 10 раз в день")
    value = re.sub(r'Мин\s+(\d+)\s+рд', r'Минимум \1 раз в день', value, flags=re.IGNORECASE)
    value = re.sub(r'Макс\s+(\d+)\s+рд', r'Максимум \1 раз в день', value, flags=re.IGNORECASE)
    
    # Общие замены (если не было совпадения выше)
    if "Минимум" not in value and "Максимум" not in value:
        value = re.sub(r'^Мин\s+', 'Минимум ', value, flags=re.IGNORECASE)
        value = re.sub(r'^Макс\s+', 'Максимум ', value, flags=re.IGNORECASE)
    
    # Замены для "рд" (если еще не заменено)
    if "раз в день" not in value:
        value = re.sub(r'\s+рд\b', ' раз в день', value, flags=re.IGNORECASE)
        value = value.replace(" р/д", " раз в день")
        value = value.replace(" р.д.", " раз в день")
        value = value.replace(" р.д", " раз в день")
    
    return value


def convert_table_to_plans_format(table_data: Dict) -> List[Dict]:
    """
    Преобразовать данные из формата таблицы в формат планов
    """
    if not table_data or "rows" not in table_data:
        return []
    
    # Получаем название раздела с маппингом
    raw_table_name = table_data.get("table_name", "Прочее")
    table_name = TABLE_NAME_MAPPING.get(raw_table_name, raw_table_name)
    # Если table_name не найден в маппинге, используем raw_table_name
    if table_name == raw_table_name and raw_table_name not in TABLE_NAME_MAPPING:
        # Пытаемся найти по имени файла (если передано)
        pass
    rows = table_data.get("rows", [])
    
    # Создаем структуру для каждого тарифа
    plans_dict = {
        "Стандарт": [],
        "Эксперт": [],
        "Оптима": [],
        "Экспресс": [],
        "Ультра": []
    }
    
    # Пропускаем заголовки (первая строка обычно заголовок)
    last_grouping = None  # Сохраняем последнее название для строк с пустым grouping
    for row in rows:
        grouping = row.get("grouping", "").strip() if row.get("grouping") else ""
        
        # Пропускаем строки-заголовки
        if grouping in ["Группировка", "Характеристики 2"]:
            continue
        
        # Если grouping пустой, но есть данные в других полях, используем последнее название
        is_continuation = False
        if not grouping:
            # Проверяем, есть ли хотя бы одно значение тарифа
            has_data = any([
                row.get("standard"), row.get("expert"), row.get("optimal"),
                row.get("express"), row.get("ultra")
            ])
            if has_data and last_grouping:
                grouping = last_grouping
                is_continuation = True  # Это продолжение предыдущей строки
            else:
                continue
        else:
            last_grouping = grouping  # Сохраняем для следующих строк
        
        # Извлекаем данные характеристики
        characteristic_name = grouping
        
        # Если это продолжение строки "Сроки", определяем что это максимум по значениям
        if is_continuation and last_grouping == "Сроки":
            # Проверяем значения на наличие "Макс"
            values = [row.get("standard"), row.get("expert"), row.get("optimal"), 
                     row.get("express"), row.get("ultra")]
            if any(v and "Макс" in str(v) for v in values):
                characteristic_name = "Максимум сроков"
        
        # Собираем все категории личных болей (personal_pain + column11 + column12)
        personal_pain_parts = []
        if row.get("personal_pain"):
            personal_pain_parts.append(row.get("personal_pain"))
        if row.get("column11"):
            personal_pain_parts.append(row.get("column11"))
        if row.get("column12"):
            personal_pain_parts.append(row.get("column12"))
        # Нормализуем и убираем дубликаты
        normalized_personal = [normalize_category(p.strip()) for p in personal_pain_parts if p and p.strip()]
        # Убираем дубликаты, сохраняя порядок
        seen_personal = set()
        unique_personal = []
        for cat in normalized_personal:
            if cat and cat not in seen_personal:
                seen_personal.add(cat)
                unique_personal.append(cat)
        personal_pain = ", ".join(unique_personal)
        # Дополнительная очистка от опечаток после объединения
        personal_pain = personal_pain.replace("Безопасностьасность", "Безопасность")
        
        # Собираем все категории корпоративных болей (corporate_pain + column14 + column15 + column16)
        corporate_pain_parts = []
        if row.get("corporate_pain"):
            corporate_pain_parts.append(row.get("corporate_pain"))
        if row.get("column14"):
            corporate_pain_parts.append(row.get("column14"))
        if row.get("column15"):
            corporate_pain_parts.append(row.get("column15"))
        if row.get("column16"):
            corporate_pain_parts.append(row.get("column16"))
        # Нормализуем и убираем дубликаты
        normalized_corporate = [normalize_category(p.strip()) for p in corporate_pain_parts if p and p.strip()]
        # Убираем дубликаты, сохраняя порядок
        seen_corporate = set()
        unique_corporate = []
        for cat in normalized_corporate:
            if cat and cat not in seen_corporate:
                seen_corporate.add(cat)
                unique_corporate.append(cat)
        corporate_pain = ", ".join(unique_corporate)
        # Дополнительная очистка от опечаток после объединения
        corporate_pain = corporate_pain.replace("Безопасностьасность", "Безопасность")
        
        characteristics_desc = row.get("characteristics", "") or ""
        advantages = row.get("advantages", "") or ""
        questions = row.get("questions", "") or ""
        objection = row.get("objection", "") or ""
        
        # Определяем, является ли это заголовком секции (только "Стоимость" и "Сроки", не продолжения)
        is_section_header = characteristic_name in ["Стоимость", "Сроки"] and not is_continuation
        
        # Добавляем характеристику в каждый тариф с соответствующим значением
        for plan_key, plan_name in PLAN_NAMES.items():
            value = row.get(plan_key, "-") or "-"
            
            # Удаляем формулы Excel (начинающиеся с =)
            if isinstance(value, str) and value.strip().startswith("="):
                value = "-"
            
            # Расшифровываем сокращения
            expanded_value = expand_abbreviations(value)
            
            char_data = {
                "раздел": table_name,
                "характеристика": characteristic_name,
                "описание": advantages or characteristics_desc,  # Используем advantages как описание
                "значение": expanded_value,
                "возражения": objection,
                "сравнение": "",  # Можно добавить из column6 если нужно
                "сомнения": questions,  # Вопросы идут в сомнения
                "личные_боли": personal_pain,
                "корпоративные_боли": corporate_pain,
                "вопросы": questions,  # Сохраняем вопросы отдельно
                "is_section_header": is_section_header,  # Флаг заголовка секции
                "raw_value": value  # Сохраняем исходное значение для прогресс-бара
            }
            
            plans_dict[plan_name].append(char_data)
    
    # Преобразуем в список планов
    plans = []
    for plan_name, characteristics in plans_dict.items():
        if characteristics:  # Добавляем только если есть характеристики
            plans.append({
                "название": plan_name,
                "цена": get_plan_price(plan_name),
                "характеристики": characteristics
            })
    
    return plans


def get_plan_price(plan_name: str) -> str:
    """Получить цену тарифа (пока заглушка, можно вынести в отдельный файл)"""
    prices = {
        "Стандарт": "220000",
        "Эксперт": "400000",
        "Оптима": "600000",
        "Экспресс": "900000",
        "Ультра": "1350000"
    }
    return prices.get(plan_name, "0")


def load_all_plans() -> List[Dict]:
    """Загрузить все тарифы из всех JSON файлов и объединить"""
    all_plans_dict = {
        "Стандарт": [],
        "Эксперт": [],
        "Оптима": [],
        "Экспресс": [],
        "Ультра": []
    }
    
    # Загружаем данные из всех файлов
    for filename in JSON_FILES:
        file_data = load_table_data(filename)
        if not file_data:
            continue
        
        # Проверяем, является ли файл массивом таблиц (как buhotch.json)
        if "tables" in file_data and isinstance(file_data["tables"], list):
            # Обрабатываем каждую таблицу в массиве
            for table_data in file_data["tables"]:
                plans = convert_table_to_plans_format(table_data)
                # Объединяем характеристики по тарифам
                for plan in plans:
                    plan_name = plan["название"]
                    if plan_name in all_plans_dict:
                        all_plans_dict[plan_name].extend(plan["характеристики"])
        else:
            # Обычный формат с одной таблицей
            plans = convert_table_to_plans_format(file_data)
            # Объединяем характеристики по тарифам
            for plan in plans:
                plan_name = plan["название"]
                if plan_name in all_plans_dict:
                    all_plans_dict[plan_name].extend(plan["характеристики"])
    
    # Преобразуем в список планов
    result_plans = []
    for plan_name, characteristics in all_plans_dict.items():
        if characteristics:
            result_plans.append({
                "название": plan_name,
                "цена": get_plan_price(plan_name),
                "характеристики": characteristics
            })
    
    return result_plans


@app.middleware("http")
async def log_requests(request, call_next):
    print(f"[REQUEST] {request.method} {request.url.path}")
    response = await call_next(request)
    print(f"[RESPONSE] {request.method} {request.url.path} - {response.status_code}")
    return response

@app.get("/")
async def root():
    return {"message": "Sales Dashboard API is running", "app": "HPV", "version": "1.0.0", "login": "/api/login"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/api/version", tags=["Meta"])
async def api_version():
    """Версия API для проверки соответствия проду и локальной сборке."""
    return {"app": "HPV", "version": "1.0.0"}

@app.get("/api/test-create")
async def test_create_endpoint():
    """Тестовый endpoint для проверки доступности /api/users/create"""
    return {"message": "Test endpoint works", "create_endpoint": "/api/users/create"}


# Эндпоинты для аутентификации
ACCESS_TOKEN_EXPIRE_MINUTES = 30


class LoginBody(BaseModel):
    username: str
    password: str


@app.post("/api/login", tags=["Authentication"])
async def login_json(body: LoginBody):
    """Вход по JSON (username, password) — альтернатива /api/token"""
    user = authenticate_user(body.username, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "roles": user.role.value if isinstance(user.role, UserRole) else user.role},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/api/token", tags=["Authentication"])
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Вход в систему"""
    try:
        print(f"Попытка входа: username={form_data.username}")
        user = authenticate_user(form_data.username, form_data.password)
        if not user:
            # Проверяем, существует ли пользователь
            db_user = get_user(form_data.username)
            if not db_user:
                print(f"Пользователь {form_data.username} не найден в базе")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Пользователь не найден",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            elif not db_user.is_active:
                print(f"Пользователь {form_data.username} заблокирован")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Пользователь заблокирован",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                print(f"Неверный пароль для пользователя {form_data.username}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Неправильный пароль",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        print(f"Успешный вход пользователя {user.username}")
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username, "roles": user.role.value if isinstance(user.role, UserRole) else user.role},
            expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Ошибка при входе: {e}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Внутренняя ошибка сервера: {str(e)}"
        )

@app.post(
    "/api/users/create",
    tags=["Admin"],
    summary="Create User",
    description="Создание нового пользователя (только для администратора)",
    dependencies=[Depends(get_current_active_admin_user)]
)
async def create_user_by_admin(
    user_create: UserCreate,
    current_user: User = Depends(get_current_active_admin_user)
):
    """Создание нового пользователя (только для администратора)"""
    try:
        print(f"[DEBUG] Создание пользователя: {user_create.username}")
        db_user = get_user(user_create.username)
        if db_user:
            raise HTTPException(status_code=400, detail="Имя пользователя уже зарегистрировано")
        new_user = create_user(user_create)
        print(f"[DEBUG] Пользователь создан успешно: {new_user.username}")
        # Возвращаем простой ответ
        return {
            "username": new_user.username,
            "email": new_user.email,
            "role": new_user.role.value if isinstance(new_user.role, UserRole) else new_user.role,
            "is_active": new_user.is_active,
            "message": "Пользователь успешно создан"
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"Ошибка при создании пользователя: {error_msg}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Ошибка: {error_msg}")

@app.get("/api/users/me", tags=["Users"])
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Получить информацию о текущем пользователе"""
    return {
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role.value if isinstance(current_user.role, UserRole) else current_user.role,
        "is_active": current_user.is_active
    }

# Эндпоинты для управления пользователями (только для администраторов)
@app.get("/api/users", tags=["Admin"])
async def get_all_users(current_user: User = Depends(get_current_active_admin_user)):
    """Получить список всех пользователей"""
    users = load_users()
    result = []
    for username, user_data in users.items():
        result.append({
            "username": username,
            "email": user_data.get("email"),
            "role": user_data.get("role", "user"),
            "is_active": user_data.get("is_active", True)
        })
    return result

@app.put("/api/users/{username}/role", tags=["Admin"])
async def update_user_role(
    username: str,
    new_role: UserRole,
    current_user: User = Depends(get_current_active_admin_user)
):
    """Обновить роль пользователя"""
    user = get_user(username)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    user.role = new_role
    updated_user = update_user(user)
    return {
        "username": updated_user.username,
        "email": updated_user.email,
        "role": updated_user.role.value if isinstance(updated_user.role, UserRole) else updated_user.role,
        "is_active": updated_user.is_active
    }

@app.put("/api/users/{username}/status", tags=["Admin"])
async def update_user_status(
    username: str,
    is_active: bool,
    current_user: User = Depends(get_current_active_admin_user)
):
    """Заблокировать/разблокировать пользователя"""
    if username == current_user.username and not is_active:
        raise HTTPException(
            status_code=400,
            detail="Нельзя заблокировать самого себя"
        )
    user = get_user(username)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    user.is_active = is_active
    updated_user = update_user(user)
    return {
        "username": updated_user.username,
        "email": updated_user.email,
        "role": updated_user.role.value if isinstance(updated_user.role, UserRole) else updated_user.role,
        "is_active": updated_user.is_active
    }


@app.get("/api/plans", tags=["Plans"])
async def get_plans(
    pain_type: Optional[str] = Query(None, description="Тип боли: personal или corporate"),
    categories: Optional[str] = Query(None, description="Категории через запятую: Легкость,Безопасность,Экономия,Скорость"),
    current_user: User = Depends(get_current_active_user)  # Требуется авторизация
):
    """
    Получить список тарифов с опциональной фильтрацией
    
    - pain_type: 'personal' для личных болей, 'corporate' для корпоративных
    - categories: список категорий через запятую
    """
    from fastapi import Response
    all_plans = load_all_plans()
    
    # Если фильтры не указаны, возвращаем все тарифы
    if not pain_type and not categories:
        return {"plans": all_plans}
    
    # Применяем фильтры
    filtered_plans = []
    category_list = [c.strip() for c in categories.split(",")] if categories else []
    
    for plan in all_plans:
        filtered_characteristics = []
        
        for char in plan.get("характеристики", []):
            should_include = True
            
            # Фильтр по типу боли
            if pain_type:
                if pain_type == "personal":
                    pain_field = char.get("личные_боли", "")
                else:  # corporate
                    pain_field = char.get("корпоративные_боли", "")
                
                if not pain_field or not pain_field.strip():
                    should_include = False
                elif category_list:
                    # Проверяем, есть ли хотя бы одна категория в поле боли
                    pain_categories = [normalize_category(c) for c in pain_field.split(",") if c.strip()]
                    normalized_category_list = [normalize_category(cat) for cat in category_list]
                    # Проверяем пересечение списков
                    if not set(normalized_category_list) & set(pain_categories):
                        should_include = False
            elif category_list:
                # Если указаны только категории, проверяем оба типа болей
                personal_pain = char.get("личные_боли", "")
                corporate_pain = char.get("корпоративные_боли", "")
                
                personal_categories = [normalize_category(c) for c in personal_pain.split(",") if personal_pain and c.strip()]
                corporate_categories = [normalize_category(c) for c in corporate_pain.split(",") if corporate_pain and c.strip()]
                
                all_categories = personal_categories + corporate_categories
                normalized_category_list = [normalize_category(cat) for cat in category_list]
                if not set(normalized_category_list) & set(all_categories):
                    should_include = False
            
            if should_include:
                filtered_characteristics.append(char)
        
        # Добавляем план только если есть отфильтрованные характеристики
        if filtered_characteristics:
            plan_copy = plan.copy()
            plan_copy["характеристики"] = filtered_characteristics
            filtered_plans.append(plan_copy)
    
    response = JSONResponse(content={"plans": filtered_plans})
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# Модель для обновления значения
class UpdateValueRequest(BaseModel):
    section: str  # Название раздела (например, "Срочность")
    characteristic: str  # Название характеристики (например, "Стоимость")
    plan_name: Optional[str] = None  # Название тарифа (например, "Стандарт"), опционально для description/questions
    new_value: str  # Новое значение
    field_type: Optional[str] = "value"  # Тип поля: "value", "description", "advantages", "questions", etc.


def find_row_in_json(file_data: Dict, section: str, characteristic: str) -> Optional[Dict]:
    """Найти строку в JSON по разделу и характеристике"""
    rows = file_data.get("rows", [])
    last_grouping = None
    
    for row in rows:
        grouping = row.get("grouping", "").strip()
        
        # Если это заголовок секции (Стоимость, Сроки), используем его
        if grouping in ["Стоимость", "Сроки"]:
            if characteristic == grouping:
                return row
            last_grouping = grouping
        # Если это обычная характеристика
        elif grouping and grouping not in ["Группировка", "Стоимость", "Сроки"]:
            if grouping == characteristic:
                return row
            last_grouping = grouping
        # Если grouping пустой, но есть данные - это может быть "Максимум сроков"
        elif not grouping and last_grouping:
            has_data = any(row.get(key) for key in ["standard", "expert", "optimal", "express", "ultra"])
            if has_data:
                # Специальный случай: "Максимум сроков" - строка после "Сроки" с "Макс" в значениях
                if characteristic == "Максимум сроков" and last_grouping == "Сроки":
                    values = [row.get("standard"), row.get("expert"), row.get("optimal"), 
                             row.get("express"), row.get("ultra")]
                    if any(v and "Макс" in str(v) for v in values):
                        return row
                # Обычное продолжение строки
                elif last_grouping == characteristic:
                    return row
    
    return None


def get_plan_key(plan_name: str) -> str:
    """Преобразовать название тарифа в ключ JSON"""
    plan_mapping = {
        "Стандарт": "standard",
        "Эксперт": "expert",
        "Оптима": "optimal",
        "Экспресс": "express",
        "Ультра": "ultra"
    }
    return plan_mapping.get(plan_name, plan_name.lower())


def get_section_filename(section: str) -> Optional[str]:
    """Найти имя файла по названию раздела (полностью динамический поиск)"""
    # Динамический поиск во всех JSON файлах
    backend_dir = os.path.dirname(__file__)
    for filename in os.listdir(backend_dir):
        if filename.endswith('.json') and filename != 'users.json':
            file_path = os.path.join(backend_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Проверяем структуру с несколькими таблицами
                if "tables" in data and isinstance(data["tables"], list):
                    for table in data["tables"]:
                        if table.get("table_name") == section:
                            return filename
                # Проверяем структуру с одной таблицей
                elif data.get("table_name") == section:
                    return filename
            except:
                continue
    
    return None


# Эндпоинты редактирования (только для администраторов)
@app.put("/api/update-value", tags=["Admin"])
async def update_value(
    request: UpdateValueRequest,
    current_user: User = Depends(get_current_active_admin_user)
):
    """Обновить значение в дашборде (только для администраторов)"""
    try:
        section_filename = get_section_filename(request.section)
        if not section_filename:
            raise HTTPException(status_code=404, detail=f"Раздел '{request.section}' не найден")
        
        file_path = os.path.join(os.path.dirname(__file__), section_filename)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"Файл для раздела '{request.section}' не найден")
        
        # Загружаем файл
        with open(file_path, "r", encoding="utf-8") as f:
            file_data = json.load(f)
        
        # Проверяем, является ли файл массивом таблиц
        if "tables" in file_data and isinstance(file_data["tables"], list):
            # Ищем нужную таблицу
            found = False
            for table_data in file_data["tables"]:
                row = find_row_in_json(table_data, request.section, request.characteristic)
                if row:
                    found = True
                    # Обновляем значение
                    if request.field_type == "value" and request.plan_name:
                        plan_key = get_plan_key(request.plan_name)
                        row[plan_key] = request.new_value
                    elif request.field_type == "description":
                        row["advantages"] = request.new_value
                    elif request.field_type == "questions":
                        row["questions"] = request.new_value
                    elif request.field_type == "personal_pain":
                        row["personal_pain"] = deduplicate_pains(request.new_value)
                        # Очищаем дополнительные колонки чтобы избежать дублирования
                        row["column11"] = ""
                        row["column12"] = ""
                    elif request.field_type == "corporate_pain":
                        row["corporate_pain"] = deduplicate_pains(request.new_value)
                        # Очищаем дополнительные колонки чтобы избежать дублирования
                        row["column14"] = ""
                        row["column15"] = ""
                        row["column16"] = ""
                    break
            if not found:
                raise HTTPException(status_code=404, detail="Характеристика не найдена")
        else:
            # Обычный формат с одной таблицей
            row = find_row_in_json(file_data, request.section, request.characteristic)
            if not row:
                raise HTTPException(status_code=404, detail="Характеристика не найдена")
            
            # Обновляем значение
            if request.field_type == "value" and request.plan_name:
                plan_key = get_plan_key(request.plan_name)
                row[plan_key] = request.new_value
            elif request.field_type == "description":
                row["advantages"] = request.new_value
            elif request.field_type == "questions":
                row["questions"] = request.new_value
            elif request.field_type == "personal_pain":
                row["personal_pain"] = deduplicate_pains(request.new_value)
                # Очищаем дополнительные колонки чтобы избежать дублирования
                row["column11"] = ""
                row["column12"] = ""
            elif request.field_type == "corporate_pain":
                row["corporate_pain"] = deduplicate_pains(request.new_value)
                # Очищаем дополнительные колонки чтобы избежать дублирования
                row["column14"] = ""
                row["column15"] = ""
                row["column16"] = ""
        
        # Сохраняем файл
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(file_data, f, ensure_ascii=False, indent=2)
        
        return {"success": True, "message": "Значение успешно обновлено"}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Ошибка при обновлении значения: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении: {str(e)}")


# ===== API для управления разделами =====

class CreateSectionRequest(BaseModel):
    name: str  # Название раздела


class RenameSectionRequest(BaseModel):
    new_name: str  # Новое название раздела


class CreateCharacteristicRequest(BaseModel):
    name: str  # Название характеристики
    standard: str = "-"  # Значение для тарифа Стандарт
    expert: str = "-"  # Значение для тарифа Эксперт
    optimal: str = "-"  # Значение для тарифа Оптима
    express: str = "-"  # Значение для тарифа Экспресс
    ultra: str = "-"  # Значение для тарифа Ультра
    advantages: str = ""  # Преимущества/описание
    questions: str = ""  # Вопросы
    personal_pain: str = ""  # Личные боли (через запятую: Легкость, Безопасность, Экономия, Скорость)
    corporate_pain: str = ""  # Корпоративные боли


def section_name_to_filename(section_name: str) -> str:
    """Преобразовать название раздела в имя файла"""
    # Транслитерация и очистка
    translit_map = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
        'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
        ' ': '_', '-': '_'
    }
    result = []
    for char in section_name.lower():
        if char in translit_map:
            result.append(translit_map[char])
        elif char.isalnum():
            result.append(char)
    return ''.join(result) + '.json'


@app.get("/api/sections", tags=["Sections"])
async def get_all_sections(current_user: User = Depends(get_current_active_user)):
    """Получить список всех разделов"""
    sections = []
    # Динамически получаем список файлов при каждом запросе
    for filename in get_all_json_files():
        file_data = load_table_data(filename)
        if not file_data:
            continue
        
        if "tables" in file_data and isinstance(file_data["tables"], list):
            for table_data in file_data["tables"]:
                table_name = table_data.get("table_name", "")
                if table_name:
                    sections.append({
                        "name": table_name,
                        "filename": filename,
                        "characteristics_count": len(table_data.get("rows", [])) - 1  # -1 for header
                    })
        else:
            table_name = file_data.get("table_name", "")
            if table_name:
                sections.append({
                    "name": table_name,
                    "filename": filename,
                    "characteristics_count": len(file_data.get("rows", [])) - 1
                })
    
    return {"sections": sections}


@app.post("/api/sections", tags=["Sections"])
async def create_section(
    request: CreateSectionRequest,
    current_user: User = Depends(get_current_active_admin_user)
):
    """Создать новый раздел (только для администраторов)"""
    try:
        # Проверяем, что раздел не существует
        existing = get_section_filename(request.name)
        if existing:
            raise HTTPException(status_code=400, detail=f"Раздел '{request.name}' уже существует")
        
        # Создаем имя файла
        filename = section_name_to_filename(request.name)
        file_path = os.path.join(os.path.dirname(__file__), filename)
        
        # Проверяем, что файл не существует
        if os.path.exists(file_path):
            raise HTTPException(status_code=400, detail=f"Файл '{filename}' уже существует")
        
        # Создаем структуру JSON для нового раздела
        new_section = {
            "table_name": request.name,
            "sheet_name": "Лист1",
            "rows": [
                {
                    "grouping": "Группировка",
                    "objection": "Возражения",
                    "personal_pain": "Боли личные",
                    "corporate_pain": "Боли корп",
                    "standard": "Стандарт",
                    "expert": "Эксперт",
                    "optimal": "Оптима",
                    "express": "Экспресс",
                    "ultra": "Ультра",
                    "advantages": "Преимущества",
                    "questions": "Вопросы"
                }
            ]
        }
        
        # Сохраняем файл
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(new_section, f, ensure_ascii=False, indent=2)
        
        # Добавляем в список файлов и маппинг
        if filename not in JSON_FILES:
            JSON_FILES.append(filename)
        
        return {"success": True, "message": f"Раздел '{request.name}' успешно создан", "filename": filename}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Ошибка при создании раздела: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Ошибка при создании раздела: {str(e)}")


@app.delete("/api/sections/{section_name}", tags=["Sections"])
async def delete_section(
    section_name: str,
    current_user: User = Depends(get_current_active_admin_user)
):
    """Удалить раздел со всеми характеристиками (только для администраторов)"""
    try:
        filename = get_section_filename(section_name)
        if not filename:
            raise HTTPException(status_code=404, detail=f"Раздел '{section_name}' не найден")
        
        file_path = os.path.join(os.path.dirname(__file__), filename)
        
        # Проверяем, содержит ли файл несколько таблиц
        file_data = load_table_data(filename)
        if file_data and "tables" in file_data and isinstance(file_data["tables"], list):
            # Файл содержит несколько таблиц - удаляем только нужную
            new_tables = [t for t in file_data["tables"] if t.get("table_name") != section_name]
            if len(new_tables) == len(file_data["tables"]):
                raise HTTPException(status_code=404, detail=f"Раздел '{section_name}' не найден в файле")
            
            if new_tables:
                # Сохраняем оставшиеся таблицы
                file_data["tables"] = new_tables
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(file_data, f, ensure_ascii=False, indent=2)
            else:
                # Удаляем файл, если таблиц больше нет
                os.remove(file_path)
                if filename in JSON_FILES:
                    JSON_FILES.remove(filename)
        else:
            # Файл содержит одну таблицу - удаляем весь файл
            os.remove(file_path)
            if filename in JSON_FILES:
                JSON_FILES.remove(filename)
        
        return {"success": True, "message": f"Раздел '{section_name}' успешно удален"}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Ошибка при удалении раздела: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Ошибка при удалении раздела: {str(e)}")


@app.put("/api/sections/{section_name}/rename", tags=["Sections"])
async def rename_section(
    section_name: str,
    request: RenameSectionRequest,
    current_user: User = Depends(get_current_active_admin_user)
):
    """Переименовать раздел (только для администраторов)"""
    try:
        # Проверяем, что раздел существует
        filename = get_section_filename(section_name)
        if not filename:
            raise HTTPException(status_code=404, detail=f"Раздел '{section_name}' не найден")
        
        # Проверяем, что новое имя не занято
        if request.new_name != section_name:
            existing = get_section_filename(request.new_name)
            if existing:
                raise HTTPException(status_code=400, detail=f"Раздел '{request.new_name}' уже существует")
        
        file_path = os.path.join(os.path.dirname(__file__), filename)
        file_data = load_table_data(filename)
        
        if file_data and "tables" in file_data and isinstance(file_data["tables"], list):
            # Файл содержит несколько таблиц - переименовываем нужную
            found = False
            for table in file_data["tables"]:
                if table.get("table_name") == section_name:
                    table["table_name"] = request.new_name
                    found = True
                    break
            if not found:
                raise HTTPException(status_code=404, detail=f"Раздел '{section_name}' не найден в файле")
        else:
            # Файл содержит одну таблицу
            file_data["table_name"] = request.new_name
        
        # Сохраняем файл
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(file_data, f, ensure_ascii=False, indent=2)
        
        return {"success": True, "message": f"Раздел переименован в '{request.new_name}'"}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Ошибка при переименовании раздела: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Ошибка при переименовании раздела: {str(e)}")


@app.post("/api/sections/{section_name}/characteristics", tags=["Sections"])
async def add_characteristic(
    section_name: str,
    request: CreateCharacteristicRequest,
    current_user: User = Depends(get_current_active_admin_user)
):
    """Добавить характеристику в раздел (только для администраторов)"""
    try:
        filename = get_section_filename(section_name)
        if not filename:
            raise HTTPException(status_code=404, detail=f"Раздел '{section_name}' не найден")
        
        file_path = os.path.join(os.path.dirname(__file__), filename)
        
        with open(file_path, "r", encoding="utf-8") as f:
            file_data = json.load(f)
        
        # Создаем новую строку характеристики
        new_row = {
            "grouping": request.name,
            "objection": "",
            "personal_pain": request.personal_pain,
            "corporate_pain": request.corporate_pain,
            "standard": request.standard,
            "expert": request.expert,
            "optimal": request.optimal,
            "express": request.express,
            "ultra": request.ultra,
            "advantages": request.advantages,
            "questions": request.questions
        }
        
        # Добавляем в нужную таблицу
        if "tables" in file_data and isinstance(file_data["tables"], list):
            for table_data in file_data["tables"]:
                if table_data.get("table_name") == section_name:
                    table_data["rows"].append(new_row)
                    break
        else:
            file_data["rows"].append(new_row)
        
        # Сохраняем файл
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(file_data, f, ensure_ascii=False, indent=2)
        
        return {"success": True, "message": f"Характеристика '{request.name}' добавлена в раздел '{section_name}'"}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Ошибка при добавлении характеристики: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Ошибка при добавлении характеристики: {str(e)}")


class RenameCharacteristicRequest(BaseModel):
    new_name: str  # Новое название характеристики


@app.put("/api/sections/{section_name}/characteristics/{characteristic_name}/rename", tags=["Sections"])
async def rename_characteristic(
    section_name: str,
    characteristic_name: str,
    request: RenameCharacteristicRequest,
    current_user: User = Depends(get_current_active_admin_user)
):
    """Переименовать характеристику (только для администраторов)"""
    try:
        filename = get_section_filename(section_name)
        if not filename:
            raise HTTPException(status_code=404, detail=f"Раздел '{section_name}' не найден")
        
        file_path = os.path.join(os.path.dirname(__file__), filename)
        
        with open(file_path, "r", encoding="utf-8") as f:
            file_data = json.load(f)
        
        found = False
        
        # Функция для поиска и переименования
        def rename_in_rows(rows, old_name, new_name):
            for row in rows:
                if row.get("grouping", "").strip() == old_name:
                    row["grouping"] = new_name
                    return True
            return False
        
        # Ищем и переименовываем в нужной таблице
        if "tables" in file_data and isinstance(file_data["tables"], list):
            for table_data in file_data["tables"]:
                if table_data.get("table_name") == section_name:
                    found = rename_in_rows(table_data.get("rows", []), characteristic_name, request.new_name)
                    break
        else:
            found = rename_in_rows(file_data.get("rows", []), characteristic_name, request.new_name)
        
        if not found:
            raise HTTPException(status_code=404, detail=f"Характеристика '{characteristic_name}' не найдена")
        
        # Сохраняем файл
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(file_data, f, ensure_ascii=False, indent=2)
        
        return {"success": True, "message": f"Характеристика переименована в '{request.new_name}'"}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Ошибка при переименовании характеристики: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Ошибка при переименовании: {str(e)}")


@app.delete("/api/sections/{section_name}/characteristics/{characteristic_name}", tags=["Sections"])
async def delete_characteristic(
    section_name: str,
    characteristic_name: str,
    current_user: User = Depends(get_current_active_admin_user)
):
    """Удалить характеристику из раздела (только для администраторов)"""
    try:
        filename = get_section_filename(section_name)
        if not filename:
            raise HTTPException(status_code=404, detail=f"Раздел '{section_name}' не найден")
        
        file_path = os.path.join(os.path.dirname(__file__), filename)
        
        with open(file_path, "r", encoding="utf-8") as f:
            file_data = json.load(f)
        
        found = False
        
        # Функция для проверки, соответствует ли строка характеристике
        def row_matches_characteristic(rows, char_name):
            last_grouping = None
            for i, row in enumerate(rows):
                grouping = row.get("grouping", "").strip()
                
                # Обычная характеристика
                if grouping == char_name:
                    return i
                
                # Сохраняем последний grouping для проверки "Максимум сроков"
                if grouping:
                    last_grouping = grouping
                # Строка с пустым grouping после "Сроки" - может быть "Максимум сроков"
                elif not grouping and last_grouping == "Сроки" and char_name == "Максимум сроков":
                    values = [row.get("standard"), row.get("expert"), row.get("optimal"), 
                             row.get("express"), row.get("ultra")]
                    if any(v and "Макс" in str(v) for v in values):
                        return i
            return -1
        
        # Удаляем из нужной таблицы
        if "tables" in file_data and isinstance(file_data["tables"], list):
            for table_data in file_data["tables"]:
                if table_data.get("table_name") == section_name:
                    idx = row_matches_characteristic(table_data["rows"], characteristic_name)
                    if idx >= 0:
                        del table_data["rows"][idx]
                        found = True
                    break
        else:
            idx = row_matches_characteristic(file_data["rows"], characteristic_name)
            if idx >= 0:
                del file_data["rows"][idx]
                found = True
        
        if not found:
            raise HTTPException(status_code=404, detail=f"Характеристика '{characteristic_name}' не найдена")
        
        # Сохраняем файл
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(file_data, f, ensure_ascii=False, indent=2)
        
        return {"success": True, "message": f"Характеристика '{characteristic_name}' удалена из раздела '{section_name}'"}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Ошибка при удалении характеристики: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Ошибка при удалении характеристики: {str(e)}")


@app.get("/api/sections/{section_name}/characteristics", tags=["Sections"])
async def get_section_characteristics(
    section_name: str,
    current_user: User = Depends(get_current_active_user)
):
    """Получить список характеристик раздела"""
    try:
        filename = get_section_filename(section_name)
        if not filename:
            raise HTTPException(status_code=404, detail=f"Раздел '{section_name}' не найден")
        
        file_path = os.path.join(os.path.dirname(__file__), filename)
        
        with open(file_path, "r", encoding="utf-8") as f:
            file_data = json.load(f)
        
        characteristics = []
        
        # Получаем характеристики из нужной таблицы
        if "tables" in file_data and isinstance(file_data["tables"], list):
            for table_data in file_data["tables"]:
                if table_data.get("table_name") == section_name:
                    rows = table_data.get("rows", [])
                    # Пропускаем заголовок (первую строку)
                    for i, row in enumerate(rows[1:], start=1):
                        characteristics.append({
                            "index": i,
                            "name": row.get("grouping", ""),
                            "personal_pain": row.get("personal_pain", ""),
                            "corporate_pain": row.get("corporate_pain", "")
                        })
                    break
        else:
            rows = file_data.get("rows", [])
            for i, row in enumerate(rows[1:], start=1):
                characteristics.append({
                    "index": i,
                    "name": row.get("grouping", ""),
                    "personal_pain": row.get("personal_pain", ""),
                    "corporate_pain": row.get("corporate_pain", "")
                })
        
        return {"characteristics": characteristics}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")


class ReorderCharacteristicsRequest(BaseModel):
    order: list  # Список названий характеристик в новом порядке


@app.put("/api/sections/{section_name}/characteristics/reorder", tags=["Sections"])
async def reorder_characteristics(
    section_name: str,
    request: ReorderCharacteristicsRequest,
    current_user: User = Depends(get_current_active_admin_user)
):
    """Изменить порядок характеристик в разделе (только для администраторов)"""
    try:
        filename = get_section_filename(section_name)
        if not filename:
            raise HTTPException(status_code=404, detail=f"Раздел '{section_name}' не найден")
        
        file_path = os.path.join(os.path.dirname(__file__), filename)
        
        with open(file_path, "r", encoding="utf-8") as f:
            file_data = json.load(f)
        
        # Функция для переупорядочивания строк
        def reorder_rows(rows, new_order):
            if not rows:
                return rows
            
            header = rows[0]  # Сохраняем заголовок
            data_rows = rows[1:]
            
            # Создаем словарь для быстрого поиска
            row_dict = {row.get("grouping"): row for row in data_rows}
            
            # Формируем новый порядок
            new_rows = [header]
            for name in new_order:
                if name in row_dict:
                    new_rows.append(row_dict[name])
                    del row_dict[name]
            
            # Добавляем оставшиеся строки (которых не было в new_order)
            new_rows.extend(row_dict.values())
            
            return new_rows
        
        # Применяем к нужной таблице
        if "tables" in file_data and isinstance(file_data["tables"], list):
            for table_data in file_data["tables"]:
                if table_data.get("table_name") == section_name:
                    table_data["rows"] = reorder_rows(table_data["rows"], request.order)
                    break
        else:
            file_data["rows"] = reorder_rows(file_data["rows"], request.order)
        
        # Сохраняем файл
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(file_data, f, ensure_ascii=False, indent=2)
        
        return {"success": True, "message": "Порядок характеристик обновлен"}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Ошибка при изменении порядка: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")


# Настройка безопасности для Swagger UI (должна быть после всех эндпоинтов)
from fastapi.openapi.utils import get_openapi

def custom_openapi():
    # Всегда генерируем схему заново, чтобы избежать проблем с кэшированием
    if hasattr(app, 'openapi_schema') and app.openapi_schema:
        app.openapi_schema = None  # Сбрасываем кэш
    openapi_schema = get_openapi(
        title="Sales Dashboard API",
        version="1.0.0",
        description="API для дашборда с подсказками для менеджеров отдела продаж",
        routes=app.routes,
    )
    # Добавляем схемы безопасности
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    openapi_schema["components"]["securitySchemes"] = {
        "Bearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    return openapi_schema

app.openapi = custom_openapi
