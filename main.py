import streamlit as st
import rac_lib as rl
from datetime import date, timedelta, datetime
import pandas as pd

st.set_page_config(page_title="Главная", page_icon="🏠", layout="wide")
rl.sidebar_pg()

st.title("🏠 Система управления студией")

@st.cache_data(ttl=5)
def load_metrics():
    metrics_map = {
        "Музыкантов": "SELECT COUNT(*) FROM musicians",
        "Коллективов": "SELECT COUNT(*) FROM bands",
        "Концертов": "SELECT COUNT(*) FROM concerts",
        "Репетиций": "SELECT COUNT(*) FROM rehearsals"
    }
    results = {}
    for label, query in metrics_map.items():
        res = rl.run_query(query)
        results[label] = res[0]['count'] if res and res[0].get('count') is not None else 0
    return results

@st.cache_data(ttl=5)
def load_upcoming_events(days=7):
    today = datetime.now()
    end_date = today + timedelta(days=days)

    events_query = """
        SELECT '🎭' as icon, concert_title as title, concert_date as dt, venue_address as loc, 'Концерт' as type
        FROM concerts WHERE concert_date BETWEEN %s AND %s
        UNION ALL
        SELECT '🎻', b.band_name, r.rehearsal_date, r.location, 'Репетиция'
        FROM rehearsals r JOIN bands b ON r.band_id = b.band_id
        WHERE r.rehearsal_date BETWEEN %s AND %s
        ORDER BY dt
    """
    return rl.run_query(events_query, (today, end_date, today, end_date))

st.subheader("📊 Статистика")
cols = st.columns(4)
metrics = load_metrics()

for col, (label, count) in zip(cols, metrics.items()):
    col.metric(label, count)

st.divider()

st.subheader("📅 Ближайшие мероприятия")
days_ahead = st.slider("Показать события на дней вперед", 1, 30, 7)

events = load_upcoming_events(days_ahead)

if events:
    df = pd.DataFrame(events)
    df['Дата'] = pd.to_datetime(df['dt']).dt.strftime('%d.%m %H:%M')
    
    for _, row in df.iterrows():
        with st.container(border=True):
            c1, c2, c3 = st.columns([0.5, 3, 1])
            c1.title(row['icon'])
            c2.write(f"**{row['title']}**")
            c2.caption(f"{row['type']} | 📍 {row['loc']}")
            c3.write(f"⏰ {row['Дата']}")
else:
    st.info("На выбранный период мероприятий нет.")