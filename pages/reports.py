import streamlit as st
import rac_lib as rl
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(page_title="Отчёты", page_icon="📊", layout="wide")
rl.sidebar_pg()

st.title("📊 Отчёты")

st.sidebar.header("Настройки")
period = st.sidebar.selectbox("Период", ["За все время", "За месяц", "За 3 месяца", "За год"])

end_date = datetime.now()
if period == "За месяц":
    start_date = end_date - timedelta(days=30)
elif period == "За 3 месяца":
    start_date = end_date - timedelta(days=90)
elif period == "За год":
    start_date = end_date - timedelta(days=365)
else:
    start_date = datetime(2000, 1, 1)

st.header("🎻 Активность репетиций (часы)")

query_rehearsals = """
    SELECT b.band_name, COUNT(*) as count, SUM(r.duration_minutes)/60.0 as hours
    FROM rehearsals r
    JOIN bands b ON r.band_id = b.band_id
    WHERE r.rehearsal_date >= %s
    GROUP BY b.band_name
    ORDER BY hours DESC LIMIT 10
"""

rehearsals_data = rl.run_query(query_rehearsals, (start_date,))

if rehearsals_data:
    df_rehearsals = pd.DataFrame(rehearsals_data)
    
    fig = px.bar(df_rehearsals, x='band_name', y='hours', 
                 title=f"Топ-10 групп по часам репетиций ({period})", 
                 labels={'band_name':'Группа', 'hours':'Часы'})
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Нет данных о репетициях за выбранный период.")

st.markdown("---")

st.header("👥 Свободные музыканты (без коллектива)")

query_solo = """
    SELECT first_name, last_name, instrument, phone 
    FROM musicians m LEFT JOIN band_membership bm ON m.musician_id = bm.musician_id 
    WHERE bm.musician_id IS NULL
    ORDER BY last_name
"""

solo = rl.run_query(query_solo)

if solo:
    df_solo = pd.DataFrame(solo)
    df_solo['instrument'] = df_solo['instrument'].map(lambda x: rl.INSTRUMENTS_REVERSE.get(x, x))
    
    st.dataframe(
        df_solo.rename(columns={
            'first_name': 'Имя',
            'last_name': 'Фамилия',
            'instrument': 'Инструмент',
            'phone': 'Телефон'
        }),
        use_container_width=True,
        hide_index=True
    )
    st.info(f"Найдено {len(df_solo)} музыкантов без коллективов")
else:
    st.info("Все музыканты в коллективах")

st.markdown("---")

st.header("🎸 Распределение по жанрам")

query_genres = """
    SELECT genre, COUNT(*) as count
    FROM bands
    GROUP BY genre
    ORDER BY count DESC
"""

genres_data = rl.run_query(query_genres)

if genres_data:
    df_genres = pd.DataFrame(genres_data)
    
    df_genres['Жанр'] = df_genres['genre'].map(lambda x: rl.GENRES_REVERSE.get(x, x))
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.dataframe(
            df_genres[['Жанр', 'count']].rename(columns={'count': 'Коллективов'}),
            use_container_width=True,
            hide_index=True
        )
    with col2:
        fig = px.pie(df_genres, values='count', names='Жанр', 
                     title='Доля коллективов по жанрам', hole=0.3)
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Нет данных о жанрах.")