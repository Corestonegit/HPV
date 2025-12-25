# Sales Dashboard - Дашборд для менеджеров отдела продаж

Проект представляет собой веб-приложение для предоставления подсказок и рекомендаций менеджерам отдела продаж.

## Структура проекта

```
.
├── backend/          # FastAPI backend
│   ├── main.py      # Основной файл приложения
│   └── requirements.txt
├── frontend/        # React frontend
│   ├── src/
│   └── package.json
└── README.md
```

## Технологии

- **Backend**: FastAPI (Python)
- **Frontend**: React + Vite
- **API**: RESTful API

## Быстрый старт

### Backend

```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload
```

Backend будет доступен на http://localhost:8000
API документация: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend будет доступен на http://localhost:3000

## Разработка

Проект находится в стадии начальной настройки. Подробное ТЗ будет добавлено позже.

