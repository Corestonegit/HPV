#!/bin/bash

# Скрипт обновления продакшена
# Использование: ./update-production.sh

set -e  # Остановка при ошибке

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}🔄 Обновление HPV проекта на продакшене...${NC}"

PROJECT_DIR="/opt/HPV"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"

# Проверка прав root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Пожалуйста, запустите скрипт от имени root${NC}"
    exit 1
fi

cd $PROJECT_DIR

# Обновление из GitHub
echo -e "${YELLOW}📥 Получение изменений из GitHub...${NC}"
git checkout main
git pull origin main

# Обновление Backend
echo -e "${YELLOW}🔧 Обновление Backend...${NC}"
cd $BACKEND_DIR
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Перезапуск Backend
echo -e "${YELLOW}🔄 Перезапуск Backend сервиса...${NC}"
systemctl restart hpv-backend
sleep 2

# Проверка статуса Backend
if systemctl is-active --quiet hpv-backend; then
    echo -e "${GREEN}✅ Backend запущен${NC}"
else
    echo -e "${RED}❌ Ошибка: Backend не запустился${NC}"
    journalctl -u hpv-backend -n 20 --no-pager
    exit 1
fi

# Обновление Frontend
echo -e "${YELLOW}🎨 Обновление Frontend...${NC}"
cd $FRONTEND_DIR
npm install
npm run build

# Проверка сборки
if [ -d "dist" ] && [ "$(ls -A dist)" ]; then
    echo -e "${GREEN}✅ Frontend собран${NC}"
else
    echo -e "${RED}❌ Ошибка: Frontend не собран${NC}"
    exit 1
fi

# Перезагрузка Nginx
echo -e "${YELLOW}🌐 Перезагрузка Nginx...${NC}"
nginx -t && systemctl reload nginx

echo -e "${GREEN}✅ Обновление завершено!${NC}"
echo ""
echo "Проверьте работу:"
echo "  - https://hpv.corestone.ru"
echo "  - https://hpv.corestone.ru/docs"
echo ""
echo "Логи Backend: journalctl -u hpv-backend -f"

