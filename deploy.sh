#!/bin/bash

# Скрипт автоматического развертывания HPV проекта на Ubuntu 24
# Использование: ./deploy.sh

set -e  # Остановка при ошибке

echo "🚀 Начало развертывания HPV проекта..."

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Проверка прав root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Пожалуйста, запустите скрипт от имени root${NC}"
    exit 1
fi

PROJECT_DIR="/opt/HPV"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"

echo -e "${YELLOW}Шаг 1: Обновление системы...${NC}"
apt update && apt upgrade -y

echo -e "${YELLOW}Шаг 2: Установка базовых пакетов...${NC}"
apt install -y curl wget git build-essential python3 python3-pip python3-venv nginx

echo -e "${YELLOW}Шаг 3: Установка Node.js...${NC}"
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt install -y nodejs
fi

echo -e "${YELLOW}Шаг 4: Клонирование репозитория...${NC}"
if [ ! -d "$PROJECT_DIR" ]; then
    cd /opt
    git clone https://github.com/Corestonegit/HPV.git
else
    echo "Репозиторий уже существует, обновляем..."
    cd $PROJECT_DIR
    git pull origin main
fi

cd $PROJECT_DIR
git checkout main

echo -e "${YELLOW}Шаг 5: Настройка Backend...${NC}"
cd $BACKEND_DIR

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Создание users.json если не существует
if [ ! -f "users.json" ]; then
    echo '{}' > users.json
    chmod 644 users.json
fi

echo -e "${YELLOW}Шаг 6: Настройка systemd сервиса...${NC}"
cat > /etc/systemd/system/hpv-backend.service << EOF
[Unit]
Description=HPV Backend API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$BACKEND_DIR
Environment="PATH=$BACKEND_DIR/venv/bin"
ExecStart=$BACKEND_DIR/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable hpv-backend
systemctl restart hpv-backend

echo -e "${YELLOW}Шаг 7: Сборка Frontend...${NC}"
cd $FRONTEND_DIR
npm install
npm run build

echo -e "${YELLOW}Шаг 8: Настройка Nginx...${NC}"
cat > /etc/nginx/sites-available/hpv.corestone.ru << EOF
server {
    listen 80;
    server_name hpv.corestone.ru;

    # Frontend (React)
    location / {
        root $FRONTEND_DIR/dist;
        try_files \$uri \$uri/ /index.html;
    }

    # Backend API
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }

    # Swagger UI
    location /docs {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }

    location /openapi.json {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
    }
}
EOF

ln -sf /etc/nginx/sites-available/hpv.corestone.ru /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

nginx -t
systemctl reload nginx

echo -e "${YELLOW}Шаг 9: Настройка Firewall...${NC}"
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

echo -e "${GREEN}✅ Развертывание завершено!${NC}"
echo ""
echo "Следующие шаги:"
echo "1. Настройте DNS запись A для hpv.corestone.ru -> 85.198.85.16"
echo "2. Установите SSL сертификат: certbot --nginx -d hpv.corestone.ru"
echo "3. Проверьте работу: https://hpv.corestone.ru"
echo ""
echo "Полезные команды:"
echo "  systemctl status hpv-backend  # Статус backend"
echo "  journalctl -u hpv-backend -f  # Логи backend"
echo "  systemctl reload nginx        # Перезагрузка nginx"

