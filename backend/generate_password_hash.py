#!/usr/bin/env python3
"""Скрипт для генерации хеша пароля"""

from passlib.context import CryptContext

# Используем ту же схему, что и в auth.py
pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Хешировать пароль"""
    return pwd_context.hash(password)

if __name__ == "__main__":
    password = "Admin@2024!Secure#Pass"
    hashed = hash_password(password)
    print(f"Пароль: {password}")
    print(f"Хеш: {hashed}")

