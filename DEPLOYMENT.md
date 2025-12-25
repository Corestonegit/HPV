# Инструкция по развертыванию проекта на Ubuntu 24

## Серверная информация
- **Домен:** hpv.corestone.ru
- **IP:** 85.198.85.16
- **ОС:** Ubuntu 24

---

## Шаг 1: Подключение к серверу

```bash
ssh root@85.198.85.16
# или
ssh root@hpv.corestone.ru
```

---

## Шаг 2: Обновление системы и установка базовых пакетов

```bash
apt update && apt upgrade -y
apt install -y curl wget git build-essential
```

---

## Шаг 3: Установка Python 3.11+ и pip

```bash
apt install -y python3 python3-pip python3-venv
python3 --version  # Должно быть 3.11 или выше
```

---

## Шаг 4: Установка Node.js 18+ (для сборки фронтенда)

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs
node --version  # Должно быть 18 или выше
npm --version
```

---

## Шаг 5: Установка Nginx

```bash
apt install -y nginx
systemctl start nginx
systemctl enable nginx
```

---

## Шаг 6: Создание пользователя для приложения (опционально, но рекомендуется)

```bash
adduser --disabled-password --gecos "" appuser
usermod -aG sudo appuser
```

---

## Шаг 7: Клонирование репозитория

```bash
cd /opt
git clone https://github.com/Corestonegit/HPV.git
cd HPV
git checkout main
```

---

## Шаг 8: Настройка Backend (FastAPI)

```bash
cd /opt/HPV/backend

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install --upgrade pip
pip install -r requirements.txt

# Создание файла users.json если его нет
touch users.json
chmod 644 users.json
```

---

## Шаг 9: Создание systemd сервиса для Backend

```bash
nano /etc/systemd/system/hpv-backend.service
```

**Содержимое файла:**
```ini
[Unit]
Description=HPV Backend API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/HPV/backend
Environment="PATH=/opt/HPV/backend/venv/bin"
ExecStart=/opt/HPV/backend/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Активация сервиса:**
```bash
systemctl daemon-reload
systemctl enable hpv-backend
systemctl start hpv-backend
systemctl status hpv-backend
```

---

## Шаг 10: Сборка Frontend

```bash
cd /opt/HPV/frontend
npm install
npm run build
```

**Результат:** папка `dist/` с собранным фронтендом

---

## Шаг 11: Настройка Nginx

```bash
nano /etc/nginx/sites-available/hpv.corestone.ru
```

**Содержимое файла:**
```nginx
server {
    listen 80;
    server_name hpv.corestone.ru;

    # Frontend (React)
    location / {
        root /opt/HPV/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # Swagger UI
    location /docs {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /openapi.json {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }
}
```

**Активация конфигурации:**
```bash
ln -s /etc/nginx/sites-available/hpv.corestone.ru /etc/nginx/sites-enabled/
rm /etc/nginx/sites-enabled/default  # Удалить дефолтный сайт если не нужен
nginx -t  # Проверка конфигурации
systemctl reload nginx
```

---

## Шаг 12: Настройка SSL (Let's Encrypt)

```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx -d hpv.corestone.ru
```

Следуйте инструкциям:
- Введите email
- Согласитесь с условиями
- Выберите редирект HTTP → HTTPS

---

## Шаг 13: Настройка Firewall (UFW)

```bash
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw enable
ufw status
```

---

## Шаг 14: Проверка работы

1. **Проверка Backend:**
   ```bash
   curl http://127.0.0.1:8000/health
   systemctl status hpv-backend
   ```

2. **Проверка Frontend:**
   Откройте в браузере: `https://hpv.corestone.ru`

3. **Проверка API:**
   Откройте: `https://hpv.corestone.ru/docs`

---

## Шаг 15: Настройка автообновления (опционально)

Создайте скрипт для обновления:

```bash
nano /opt/HPV/update.sh
```

**Содержимое:**
```bash
#!/bin/bash
cd /opt/HPV
git pull origin main
cd backend
source venv/bin/activate
pip install -r requirements.txt
systemctl restart hpv-backend
cd ../frontend
npm install
npm run build
systemctl reload nginx
echo "Update completed!"
```

**Сделать исполняемым:**
```bash
chmod +x /opt/HPV/update.sh
```

---

## Полезные команды для управления

```bash
# Перезапуск Backend
systemctl restart hpv-backend

# Просмотр логов Backend
journalctl -u hpv-backend -f

# Перезапуск Nginx
systemctl reload nginx

# Просмотр логов Nginx
tail -f /var/log/nginx/error.log
tail -f /var/log/nginx/access.log
```

---

## Важные замечания

1. **Безопасность:**
   - Убедитесь, что `users.json` не содержит чувствительных данных в git
   - Настройте регулярные бэкапы
   - Используйте сильные пароли для админа

2. **Производительность:**
   - Для продакшена рассмотрите использование Gunicorn с несколькими воркерами
   - Настройте кэширование в Nginx

3. **Мониторинг:**
   - Настройте мониторинг сервисов
   - Настройте алерты при падении сервисов

---

## Обновление проекта

```bash
cd /opt/HPV
git pull origin main
cd backend
source venv/bin/activate
pip install -r requirements.txt
systemctl restart hpv-backend
cd ../frontend
npm install
npm run build
systemctl reload nginx
```

---

## Troubleshooting

**Backend не запускается:**
```bash
systemctl status hpv-backend
journalctl -u hpv-backend -n 50
```

**Nginx ошибки:**
```bash
nginx -t
tail -f /var/log/nginx/error.log
```

**Проблемы с портами:**
```bash
netstat -tulpn | grep :8000
lsof -i :8000
```

