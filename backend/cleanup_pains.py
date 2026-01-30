#!/usr/bin/env python3
"""
Скрипт для очистки и консолидации болей в JSON файлах.
Переносит все боли из column11-16 в основные поля personal_pain и corporate_pain,
удаляет дубликаты и очищает дополнительные колонки.
"""

import json
import os
import glob

VALID_CATEGORIES = {"Легкость", "Безопасность", "Экономия", "Скорость"}

def normalize_category(cat: str) -> str:
    """Нормализация категорий болей"""
    if not cat:
        return ""
    cat = cat.strip()
    
    # Сначала обрабатываем комбинированные ошибки
    cat = cat.replace("Безопасностьасность", "Безопасность")
    cat = cat.replace("Безопасность, Безопасность", "Безопасность")
    cat = cat.replace("Безопасность,Безопасность", "Безопасность")
    
    # Нормализация вариантов написания
    cat = cat.replace("Лёгкость", "Легкость").replace("лёгкость", "легкость")
    cat = cat.replace("Лекость", "Легкость")
    cat = cat.replace("Безопастность", "Безопасность")
    
    # Сокращения - только если это точно сокращение (начало слова)
    if cat == "Безоп":
        cat = "Безопасность"
    if cat == "Эконом":
        cat = "Экономия"
    if cat == "Сроки":
        cat = "Скорость"
    
    # Проверяем что это валидная категория
    if cat in VALID_CATEGORIES:
        return cat
    
    # Если всё ещё не валидная, пробуем найти частичное совпадение
    cat_lower = cat.lower()
    if "легк" in cat_lower or "лёгк" in cat_lower:
        return "Легкость"
    if "безоп" in cat_lower:
        return "Безопасность"
    if "эконом" in cat_lower:
        return "Экономия"
    if "скор" in cat_lower or "срок" in cat_lower:
        return "Скорость"
    
    # Если ничего не подошло, возвращаем пустую строку (игнорируем невалидные)
    if cat and cat not in VALID_CATEGORIES:
        print(f"  [WARN] Неизвестная категория: '{cat}'")
        return ""
    
    return cat

def deduplicate_pains(pains_list):
    """Удаление дубликатов с сохранением порядка"""
    seen = set()
    unique = []
    for p in pains_list:
        normalized = normalize_category(p)
        if normalized and normalized not in seen:
            seen.add(normalized)
            unique.append(normalized)
    return unique

def process_row(row):
    """Обработка одной строки - консолидация болей"""
    # Собираем личные боли
    personal_parts = []
    if row.get("personal_pain"):
        personal_parts.append(row["personal_pain"])
    if row.get("column11"):
        personal_parts.append(row["column11"])
    if row.get("column12"):
        personal_parts.append(row["column12"])
    
    # Собираем корпоративные боли
    corporate_parts = []
    if row.get("corporate_pain"):
        corporate_parts.append(row["corporate_pain"])
    if row.get("column14"):
        corporate_parts.append(row["column14"])
    if row.get("column15"):
        corporate_parts.append(row["column15"])
    if row.get("column16"):
        corporate_parts.append(row["column16"])
    
    # Дедуплицируем
    unique_personal = deduplicate_pains(personal_parts)
    unique_corporate = deduplicate_pains(corporate_parts)
    
    # Записываем в основные поля
    row["personal_pain"] = ", ".join(unique_personal)
    row["corporate_pain"] = ", ".join(unique_corporate)
    
    # Очищаем дополнительные колонки (боли теперь в основных полях)
    row["column11"] = ""
    row["column12"] = ""
    row["column14"] = ""
    row["column15"] = ""
    row["column16"] = ""
    
    return row

def process_file(filepath):
    """Обработка одного JSON файла"""
    print(f"Обрабатываю: {filepath}")
    
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    changes_made = 0
    
    if "tables" in data and isinstance(data["tables"], list):
        for table in data["tables"]:
            if "rows" in table:
                for row in table["rows"]:
                    old_personal = row.get("personal_pain", "")
                    old_corporate = row.get("corporate_pain", "")
                    process_row(row)
                    if row["personal_pain"] != old_personal or row["corporate_pain"] != old_corporate:
                        changes_made += 1
    elif "rows" in data:
        for row in data["rows"]:
            old_personal = row.get("personal_pain", "")
            old_corporate = row.get("corporate_pain", "")
            process_row(row)
            if row["personal_pain"] != old_personal or row["corporate_pain"] != old_corporate:
                changes_made += 1
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"  Изменено записей: {changes_made}")
    return changes_made

def main():
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    json_files = glob.glob(os.path.join(backend_dir, "*.json"))
    
    # Исключаем users.json
    json_files = [f for f in json_files if not f.endswith("users.json")]
    
    total_changes = 0
    for filepath in json_files:
        total_changes += process_file(filepath)
    
    print(f"\nВсего изменено записей: {total_changes}")

if __name__ == "__main__":
    main()
