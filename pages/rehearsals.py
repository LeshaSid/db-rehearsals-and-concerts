import streamlit as st
import rac_lib as rl
from datetime import date, time, timedelta, datetime
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Репетиции", page_icon="🎻", layout="wide")
rl.sidebar_pg()

st.title("🎻 Управление репетициями")

TIME_SLOTS = [time(h) for h in range(8, 24)]
DURATIONS = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0]

@st.cache_data(ttl=1)
def load_bands():
    data = rl.run_query("SELECT band_id, band_name FROM bands ORDER BY band_name")
    return {b['band_name']: b['band_id'] for b in data}, [b['band_name'] for b in data]

@st.cache_data(ttl=1)
def load_rehearsals_for_day(target_date):
    start_dt = datetime.combine(target_date, time.min) 
    end_dt = datetime.combine(target_date, time.max)
    
    query = """
        SELECT r.*, b.band_name
        FROM rehearsals r
        JOIN bands b ON r.band_id = b.band_id
        WHERE r.rehearsal_date BETWEEN %s AND %s
        ORDER BY r.rehearsal_date
    """
    return rl.run_query(query, (start_dt, end_dt))

@st.cache_data(ttl=1)
def load_future_rehearsals(days=30):
    start_dt = datetime.combine(date.today(), time.min)
    end_dt = start_dt + timedelta(days=days)
    
    query = """
        SELECT r.*, b.band_name
        FROM rehearsals r
        JOIN bands b ON r.band_id = b.band_id
        WHERE r.rehearsal_date BETWEEN %s AND %s
        ORDER BY r.rehearsal_date
    """
    return rl.run_query(query, (start_dt, end_dt))

try:
    bands_map, bands_list = load_bands()
except:
    bands_map, bands_list = {}, []

if not bands_list:
    st.warning("⚠️ Сначала создайте коллектив на вкладке 'Коллективы'")
    st.stop()

tab1, tab2, tab3 = st.tabs(["📅 Забронировать", "📋 Расписание", "⚙️ Управление"])

with tab1:
    st.subheader("Бронирование репетиции")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        booking_date = st.date_input("Дата репетиции", min_value=date.today())
        
        occupied = load_rehearsals_for_day(booking_date)
        
        if occupied:
            
            df = pd.DataFrame(occupied)
            df['start'] = pd.to_datetime(df['rehearsal_date'])
            df['end'] = df['start'] + pd.to_timedelta(df['duration_minutes'], unit='m')
            df['Зал'] = df['location']
            df['Группа'] = df['band_name']
            
            start_day = datetime.combine(booking_date, time.min)
            
            fig = px.timeline(df, x_start="start", x_end="end", y="Зал", color="Группа", 
                              title=f"График занятости на {booking_date.strftime('%d.%m.%Y')}",
                              height=400)
            
            fig.update_yaxes(categoryorder="array", categoryarray=rl.LOCATIONS)
                
            fig.update_xaxes(
                tickformat="%H:%M", 
                range=[start_day + timedelta(hours=8), start_day + timedelta(hours=23)] # 8:00 - 23:00
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("На этот день репетиций нет. Все залы свободны!")
            
    with col2:
        with st.form("booking_form", clear_on_submit=True):
            band = st.selectbox("Коллектив*", bands_list)
            start_time = st.selectbox("Время начала*", TIME_SLOTS, format_func=lambda t: t.strftime("%H:%M"))
            duration = st.selectbox("Длительность (часы)*", DURATIONS)
            location = st.selectbox("Место*", rl.LOCATIONS)
            
            submitted = st.form_submit_button("Забронировать", type="primary", use_container_width=True)
            
            if submitted:
                if not band or not start_time or not duration or not location:
                    st.error("❌ Заполните все обязательные поля")
                else:
                    start_dt = datetime.combine(booking_date, start_time)
                    end_dt = start_dt + timedelta(hours=duration)
                    
                    has_conflict = False
                    occupied = load_rehearsals_for_day(booking_date)
                    for r in occupied:
                        r_start = r['rehearsal_date']
                        r_end = r_start + timedelta(minutes=r['duration_minutes'])
                        
                        if (start_dt < r_end) and (end_dt > r_start) and (location == r['location']):
                            has_conflict = True
                            st.error(f"❌ Конфликт с репетицией {r['band_name']} в зале {r['location']}")
                            break
                    
                    if not has_conflict:
                        band_id = bands_map[band]
                        duration_minutes = int(duration * 60)
                        
                        query = """
                            INSERT INTO rehearsals (band_id, rehearsal_date, duration_minutes, location) 
                            VALUES (%s, %s, %s, %s)
                        """
                        
                        if rl.execute_non_query(query, (band_id, start_dt, duration_minutes, location)):
                            st.toast("✅ Репетиция забронирована!", icon="📅")
                            load_rehearsals_for_day.clear()
                            load_future_rehearsals.clear()
                        else:
                            st.error("❌ Ошибка при бронировании")

with tab2:
    st.subheader("Расписание репетиций")
    
    days = st.slider("Показать на дней вперед", 1, 90, 30)
    
    rehearsals = load_future_rehearsals(days)
    
    if rehearsals:
        df = pd.DataFrame(rehearsals)
        df['Дата и время'] = pd.to_datetime(df['rehearsal_date']).dt.strftime('%d.%m.%Y %H:%M')
        df['Продолжительность (ч)'] = (df['duration_minutes'] / 60).round(1)
        df['Конец'] = pd.to_datetime(df['rehearsal_date']) + pd.to_timedelta(df['duration_minutes'], unit='m')
        df['Конец'] = df['Конец'].dt.strftime('%H:%M')
        
        col1, col2 = st.columns(2)
        with col1:
            filter_band = st.selectbox("Фильтр по коллективу", ["Все"] + bands_list)
        with col2:
            filter_location = st.selectbox("Фильтр по месту", ["Все"] + rl.LOCATIONS)
        
        if filter_band != "Все":
            df = df[df['band_name'] == filter_band]
        if filter_location != "Все":
            df = df[df['location'] == filter_location]
        
        st.dataframe(
            df[['Дата и время', 'band_name', 'Продолжительность (ч)', 'location', 'Конец']].rename(
                columns={'band_name': 'Коллектив', 'location': 'Место'}
            ),
            use_container_width=True,
            hide_index=True
        )
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Всего репетиций", len(df))
        with col2:
            total_hours = df['Продолжительность (ч)'].sum()
            st.metric("Всего часов", f"{total_hours:.1f}")
        with col3:
            unique_bands = df['band_name'].nunique() 
            st.metric("Уникальных коллективов", unique_bands)
    else:
        st.info("Нет запланированных репетиций на выбранный период")

with tab3:
    st.subheader("Управление репетициями")
    
    rehearsals = load_future_rehearsals(90)
    
    if not rehearsals:
        st.info("Нет активных репетиций")
    else:
        rehearsals_map = {f"{r['band_name']} - {r['rehearsal_date'].strftime('%d.%m.%Y %H:%M')}": r for r in rehearsals}
        selected_name = st.selectbox("Выберите репетицию", list(rehearsals_map.keys()))
        
        if selected_name:
            rehearsal = rehearsals_map[selected_name]
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                with st.form("edit_form"):
                    st.write(f"**Текущая репетиция:** {rehearsal['band_name']}")
                    
                    new_date = st.date_input("Новая дата", value=rehearsal['rehearsal_date'].date(), min_value=date.today())
                    
                    try:
                        current_time = rehearsal['rehearsal_date'].time()
                        time_index = TIME_SLOTS.index(current_time) if current_time in TIME_SLOTS else 0
                    except:
                        time_index = 0
                    
                    new_time = st.selectbox("Новое время", TIME_SLOTS, index=time_index, format_func=lambda t: t.strftime("%H:%M"))
                    
                    try:
                        current_duration = rehearsal['duration_minutes'] / 60
                        dur_index = DURATIONS.index(current_duration) if current_duration in DURATIONS else 0
                    except:
                        dur_index = 0
                    
                    new_duration = st.selectbox("Новая длительность (часы)", DURATIONS, index=dur_index)
                    
                    try:
                        current_location = rehearsal['location']
                        loc_index = rl.LOCATIONS.index(current_location) if current_location in rl.LOCATIONS else 0
                    except: 
                        loc_index = 0
                    
                    new_location = st.selectbox("Новое место", rl.LOCATIONS, index=loc_index)
                    
                    submitted = st.form_submit_button("Сохранить изменения", type="primary", use_container_width=True)
                    
                    if submitted:
                        new_dt = datetime.combine(new_date, new_time)
                        new_minutes = int(new_duration * 60)
                        
                        occupied = load_rehearsals_for_day(new_date)
                        occupied = [r for r in occupied if r['rehearsal_id'] != rehearsal['rehearsal_id']]
                        
                        has_conflict = False
                        for r in occupied:
                            r_start = r['rehearsal_date']
                            r_end = r_start + timedelta(minutes=r['duration_minutes'])
                            new_end = new_dt + timedelta(minutes=new_minutes)
                            
                            if (new_dt < r_end) and (new_end > r_start) and (new_location == r['location']):
                                has_conflict = True
                                st.error(f"❌ Конфликт с репетицией {r['band_name']} в зале {r['location']}")
                                break
                        
                        if not has_conflict:
                            query = """
                                UPDATE rehearsals 
                                SET rehearsal_date=%s, duration_minutes=%s, location=%s 
                                WHERE rehearsal_id=%s
                            """
                            
                            if rl.execute_non_query(query, (new_dt, new_minutes, new_location, rehearsal['rehearsal_id'])):
                                st.toast("✅ Репетиция обновлена!", icon="📝")
                                load_rehearsals_for_day.clear()
                                load_future_rehearsals.clear()
                                st.rerun()
                            else:
                                st.error("❌ Ошибка при обновлении")
            
            with col2:
                st.markdown("### Действия")
                
                if st.button("❌ Отменить репетицию", type="secondary", use_container_width=True):
                    query = "DELETE FROM rehearsals WHERE rehearsal_id = %s"
                    if rl.execute_non_query(query, (rehearsal['rehearsal_id'],)):
                        st.toast("✅ Репетиция отменена!", icon="🗑️")
                        load_rehearsals_for_day.clear()
                        load_future_rehearsals.clear()
                        st.rerun()
                    else:
                        st.error("❌ Ошибка при отмене")