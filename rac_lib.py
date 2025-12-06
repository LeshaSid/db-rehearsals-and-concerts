import streamlit as st 
import psycopg2 
import pandas as pd
from contextlib import contextmanager
from datetime import datetime, timedelta 
import time 

# --- КОНСТАНТЫ (Соответствуют ограничениям SQL) ---

# Константы для репетиций
LOCATIONS = ['Большой зал', 'Малый зал', 'Студия А', 'Студия Б'] # <-- ДОБАВЛЕНО

# Константы для музыкантов
INSTRUMENTS = {
    "Гитара": "guitar", "Бас": "bass", "Барабаны": "drums", "Клавишные": "keyboards",
    "Пианино": "piano", "Вокал": "vocals", "Скрипка": "violin", "Виолончель": "cello",
    "Труба": "trumpet", "Саксофон": "saxophone", "Тромбон": "trombone", "Флейта": "flute",
    "Кларнет": "clarinet", "Аккордеон": "accordion", "Арфа": "harp"
}
INSTRUMENTS_REVERSE = {v: k for k, v in INSTRUMENTS.items()}
INSTRUMENTS_LIST = list(INSTRUMENTS.keys())

# Константы для коллективов
GENRES = {
    "Рок": "rock", "Поп": "pop", "Джаз": "jazz", "Блюз": "blues", "Классика": "classical",
    "Электроника": "electronic", "Фолк": "folk", "Метал": "metal", "Панк": "punk",
    "Регги": "reggae", "Хип-хоп": "hip-hop", "Кантри": "country", "Фанк": "funk",
    "Соул": "soul", "R&B": "r&b", "Альтернатива": "alternative", "Инди": "indie",
    "Хард-рок": "hard_rock", "Прогрессив": "progressive", "Хаус": "house", "Техно": "techno"
}
GENRES_REVERSE = {v: k for k, v in GENRES.items()}
GENRES_LIST = list(GENRES.keys())

# --- ФУНКЦИИ ДЛЯ РАБОТЫ С БАЗОЙ ДАННЫХ (PostgreSQL) ---

# Создаем соединение без кэширования, так как Streamlit сам управляет кэшем
def init_connection():
    try:
        # Убедитесь, что здесь указаны ваши корректные данные для подключения
        conn = psycopg2.connect(
            host="localhost", 
            database="concerts and rehearsals", 
            user="postgres", 
            password="",
            port=5432
        )
        return conn
    except Exception as e:
        st.error(f"❌ Ошибка подключения к базе данных: {e}")
        st.info("Проверьте, запущен ли PostgreSQL, и обновите учетные данные.")
        return None

# Функция для выполнения запроса SELECT и возврата данных
@st.cache_data(ttl=60)
def run_query(query, params=None):
    conn = init_connection()
    if conn is None:
        return []
        
    cursor = conn.cursor()
    try:
        cursor.execute(query, params or ())
        if cursor.description:  # Проверяем, есть ли результат
            column_names = [desc[0] for desc in cursor.description]
            results = [dict(zip(column_names, row)) for row in cursor.fetchall()]
            return results
        return []
    except Exception as e:
        st.error(f"❌ Ошибка выполнения запроса: {e}")
        return []
    finally:
        if 'cursor' in locals() and cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()

# Функция для выполнения запросов INSERT, UPDATE, DELETE
def execute_non_query(query, params=None, fetch_id=False):
    conn = init_connection()
    if conn is None:
        return None if fetch_id else False

    cursor = conn.cursor()
    try:
        cursor.execute(query, params or ())
        if fetch_id:
            result = cursor.fetchone()
            conn.commit()
            return result[0] if result else None
        else:
            conn.commit()
            return True
    except Exception as e:
        conn.rollback()
        st.error(f"❌ Ошибка транзакции: {e}")
        return None if fetch_id else False
    finally:
        if 'cursor' in locals() and cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()

# Универсальная функция удаления
def delete_record(table, id_column, record_id):
    """Универсальное удаление записи."""
    try:
        sql = f"DELETE FROM {table} WHERE {id_column} = %s"
        return execute_non_query(sql, (record_id,))
    except Exception as e:
        st.error(f"Ошибка удаления: {e}")
        return False

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def sidebar_pg():
    with st.sidebar:
        st.header("🎵 Меню")
        
        pages = {
            "main.py": "🏠 Главная",
            "pages/musicans.py": "🎵 Музыканты",
            "pages/bands.py": "🎸 Коллективы",
            "pages/concerts.py": "🎭 Концерты",
            "pages/rehearsals.py": "🎻 Репетиции",
            "pages/reports.py": "📊 Отчеты"
        }
        
        for page_path, icon_label in pages.items():
            st.page_link(page_path, label=icon_label)
        
        st.divider()
        st.markdown(f"Version 0.1.0 (Streamlit {st.__version__})")