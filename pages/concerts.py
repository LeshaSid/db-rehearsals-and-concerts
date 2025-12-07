import streamlit as st
import rac_lib as rl
import pandas as pd
from datetime import date, time, datetime

st.set_page_config(page_title="Концерты", page_icon="🎭", layout="wide")
rl.sidebar_pg()

st.title("🎭 Концерты")

@st.cache_data(ttl=1)
def load_bands():
    data = rl.run_query("SELECT band_id, band_name FROM bands ORDER BY band_name")
    return {b['band_name']: b['band_id'] for b in data}, [b['band_name'] for b in data]

@st.cache_data(ttl=1)
def load_concerts():
    query = """
        SELECT c.*, 
               COUNT(p.performance_id) as band_count,
               STRING_AGG(b.band_name, ', ') as bands_list
        FROM concerts c
        LEFT JOIN performances p ON c.concert_id = p.concert_id
        LEFT JOIN bands b ON p.band_id = b.band_id
        GROUP BY c.concert_id
        ORDER BY c.concert_date DESC
    """
    return rl.run_query(query)

@st.cache_data(ttl=1)
def load_concert_lineup(concert_id):
    query = """
        SELECT b.band_name, p.performance_order
        FROM performances p
        JOIN bands b ON p.band_id = b.band_id
        WHERE p.concert_id = %s
        ORDER BY p.performance_order NULLS LAST, b.band_name
    """
    return rl.run_query(query, (concert_id,))

bands_map, bands_list = load_bands()
concerts_data = load_concerts()

st.subheader("📋 Все концерты")

if concerts_data:
    df = pd.DataFrame(concerts_data)
    df['Дата и время'] = pd.to_datetime(df['concert_date']).dt.strftime('%d.%m.%Y %H:%M')
    df['Коллективы'] = df['bands_list'].fillna('Не указаны')
    df_display = df.rename(columns={
        'concert_title': 'Название',
        'venue_address': 'Адрес',
        'band_count': 'Кол-во групп'
    })
    
    search = st.text_input("🔍 Поиск по названию или адресу")
    if search:
        mask = df_display['Название'].str.contains(search, case=False) | \
               df_display['Адрес'].str.contains(search, case=False)
        df_display = df_display[mask]
    
    st.dataframe(
        df_display[['Название', 'Адрес', 'Дата и время', 'Кол-во групп', 'Коллективы']],
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("В базе данных пока нет концертов.")

st.markdown("---")

tab1, tab2, tab3 = st.tabs(["➕ Создать", "✏️ Редактировать", "🗑️ Удалить"])

with tab1:
    with st.form("create_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            title = st.text_input("Название концерта*")
            address = st.text_input("Адрес*")
        
        with col2:
            concert_date = st.date_input("Дата*", value=date.today())
            concert_time = st.time_input("Время*", value=time(20, 0))
        
        selected_bands = st.multiselect("Коллективы", bands_list)
        
        st.markdown("\\* - обязательные поля")
        
        submitted = st.form_submit_button("Создать", type="primary", use_container_width=True)
        
        if submitted:
            if not title or not address:
                st.error("Название и адрес обязательны")
            else:
                full_datetime = datetime.combine(concert_date, concert_time)
                
                query = """
                    INSERT INTO concerts (concert_title, venue_address, concert_date) 
                    VALUES (%s, %s, %s)
                """
                success = rl.execute_non_query(query, (title, address, full_datetime))
                
                if success:
                    get_id_query = "SELECT concert_id FROM concerts WHERE concert_title = %s AND venue_address = %s AND concert_date = %s ORDER BY concert_id DESC LIMIT 1"
                    concert_id_result = rl.run_query(get_id_query, (title, address, full_datetime))
                    
                    if concert_id_result:
                        concert_id = concert_id_result[0]['concert_id']
                        
                        all_success = True
                        for i, band_name in enumerate(selected_bands, 1):
                            band_id = bands_map.get(band_name)
                            if band_id:
                                perf_query = "INSERT INTO performances (concert_id, band_id, performance_order) VALUES (%s, %s, %s)"
                                if not rl.execute_non_query(perf_query, (concert_id, band_id, i)):
                                    all_success = False
                                    st.error(f"Ошибка при добавлении коллектива: {band_name}")
                        
                        if all_success:
                            st.success("✅ Концерт создан!")
                            load_concerts.clear()
                            st.rerun()
                    else:
                        st.error("❌ Не удалось получить ID созданного концерта")
                else:
                    st.error("❌ Ошибка при создании концерта")

with tab2:
    if not concerts_data:
        st.info("Нет концертов для редактирования")
    else:
        concert_options = {f"{c['concert_title']} ({c['concert_date'].strftime('%d.%m.%Y')})": c for c in concerts_data}
        selected_display = st.selectbox(
            "Выберите концерт",
            list(concert_options.keys()),
            index=None
        )
        
        if selected_display:
            concert = concert_options[selected_display]
            lineup = load_concert_lineup(concert['concert_id'])
            current_bands = [band['band_name'] for band in lineup]
            
            with st.form("edit_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    new_title = st.text_input("Название*", value=concert['concert_title'])
                    new_address = st.text_input("Адрес*", value=concert['venue_address'])
                
                with col2:
                    current_dt = concert['concert_date']
                    if isinstance(current_dt, str):
                        current_dt = datetime.fromisoformat(current_dt.replace('Z', '+00:00'))
                    
                    new_date = st.date_input("Дата*", value=current_dt.date())
                    new_time = st.time_input("Время*", value=current_dt.time())
                
                new_bands = st.multiselect("Коллективы", bands_list, default=current_bands)
                
                submitted = st.form_submit_button("Сохранить", type="primary", use_container_width=True)
                
                if submitted:
                    if not new_title or not new_address:
                        st.error("Название и адрес обязательны")
                    else:
                        new_datetime = datetime.combine(new_date, new_time)
                        
                        update_query = """
                            UPDATE concerts 
                            SET concert_title=%s, venue_address=%s, concert_date=%s 
                            WHERE concert_id=%s
                        """
                        success = rl.execute_non_query(
                            update_query, 
                            (new_title, new_address, new_datetime, concert['concert_id'])
                        )
                        
                        if success:
                            rl.execute_non_query("DELETE FROM performances WHERE concert_id = %s", (concert['concert_id'],))
                            
                            for i, band_name in enumerate(new_bands, 1):
                                band_id = bands_map.get(band_name)
                                if band_id:
                                    perf_query = "INSERT INTO performances (concert_id, band_id, performance_order) VALUES (%s, %s, %s)"
                                    rl.execute_non_query(perf_query, (concert['concert_id'], band_id, i))
                            
                            st.success("✅ Концерт обновлен!")
                            load_concerts.clear()
                            st.rerun()
                        else:
                            st.error("❌ Ошибка при обновлении")

with tab3:
    if not concerts_data:
        st.info("Нет концертов для удаления")
    else:
        concert_options = {f"{c['concert_title']} ({c['concert_date'].strftime('%d.%m.%Y')})": c['concert_id'] for c in concerts_data}
        to_delete = st.multiselect("Выберите концерты для удаления", list(concert_options.keys()))
        
        if to_delete:
            st.warning(f"Будет удалено {len(to_delete)} концертов")
            
            with st.expander("Список для удаления"):
                for name in to_delete:
                    st.write(f"• {name}")
            
            confirm = st.checkbox("Подтвердить удаление")
            
            if st.button("Удалить", type="primary", disabled=not confirm):
                ids_to_delete = [concert_options[name] for name in to_delete]
                
                placeholders = ', '.join(['%s'] * len(ids_to_delete))
                
                delete_perf = f"DELETE FROM performances WHERE concert_id IN ({placeholders})"
                rl.execute_non_query(delete_perf, ids_to_delete)
                
                delete_concerts = f"DELETE FROM concerts WHERE concert_id IN ({placeholders})"
                success = rl.execute_non_query(delete_concerts, ids_to_delete)
                
                if success:
                    st.success(f"✅ Удалено {len(to_delete)} концертов")
                    load_concerts.clear()
                    st.rerun()
                else:
                    st.error("❌ Ошибка при удалении")