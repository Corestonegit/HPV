# Backend - FastAPI

## Установка

```bash
# Создать виртуальное окружение
python -m venv venv

# Активировать виртуальное окружение
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt
```

## Запуск

```bash
# Запуск сервера разработки
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Или через Python
python -m uvicorn main:app --reload
```

API будет доступен по адресу: http://localhost:8000

Документация API (Swagger): http://localhost:8000/docs

