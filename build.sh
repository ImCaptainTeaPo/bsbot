#!/bin/bash

# Создаём виртуальное окружение на Python 3.11
python3.11 -m venv venv
source venv/bin/activate

# Устанавливаем зависимости
pip install --upgrade pip
pip install -r requirements.txt
