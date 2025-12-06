import streamlit as st
import rac_lib as rl
import pandas as pd
from datetime import date
import time

st.set_page_config(page_title="Коллективы", page_icon="🎸", layout="wide")
rl.sidebar_pg()
st.title("🎸 Музыкальные коллективы")

@st.cache_data(ttl=60)
def load_bands():
    query = """
        SELECT b.*, 
               COUNT(DISTINCT bm.musician_id) as members,
               COUNT(DISTINCT r.rehearsal_id) as rehearsals_count
        FROM bands b
        LEFT JOIN band_membership bm ON b.band_id = bm.band_id
        LEFT JOIN rehearsals r ON b.band_id = r.band_id
        GROUP BY b.band_id
        ORDER BY b.band_name
    """
    data = rl.run_query(query)
    for b in data:
        b['genre_display'] = rl.GENRES_REVERSE.get(b['genre'], b['genre'])
    return data

@st.cache_data(ttl=60)
def load_band_members(band_id):
    query = """
        SELECT m.first_name, m.last_name, m.instrument, bm.musician_id 
        FROM band_membership bm JOIN musicians m ON bm.musician_id = m.musician_id 
        WHERE bm.band_id = %s ORDER BY m.last_name
    """
    members = rl.run_query(query, (band_id,))
    for m in members:
        m['instrument_display'] = rl.INSTRUMENTS_REVERSE.get(m['instrument'], m['instrument'])
    return members

@st.cache_data(ttl=60)
def load_available_musicians(band_id):
    query = """
        SELECT musician_id, first_name, last_name, instrument FROM musicians 
        WHERE musician_id NOT IN (SELECT musician_id FROM band_membership WHERE band_id = %s)
        ORDER BY last_name
    """
    available = rl.run_query(query, (band_id,))
    return available

bands = load_bands()
if not bands:
    st.info("Коллективов нет. Создайте первый во вкладке 'Создать'.")

bands_map = {b['band_name']: b['band_id'] for b in bands}

tab1, tab2, tab3 = st.tabs(["Список", "Создать/Ред.", "Состав"])

with tab1:
    if bands:
        df = pd.DataFrame(bands)
        st.dataframe(df[['band_name', 'genre_display', 'founded_date', 'members', 'rehearsals_count']].rename(
            columns={'band_name': 'Название', 'genre_display': 'Жанр', 'founded_date': 'Основан', 
                     'members': 'Участники', 'rehearsals_count': 'Репетиций (за все время)'}), 
            use_container_width=True, hide_index=True)
    
with tab2:
    is_edit = st.toggle("Режим редактирования")
    target_band = None
    
    if is_edit and bands:
        s_name = st.selectbox("Выберите группу", list(bands_map.keys()))
        target_band = next(b for b in bands if b['band_name'] == s_name)
    
    if is_edit and not bands:
        st.info("Нет коллективов для редактирования.")

    with st.form("band_form"):
        st.markdown(f"##### {'Редактирование' if is_edit else 'Создание'} коллектива")
        b_name = st.text_input("Название*", value=target_band['band_name'] if target_band else "")
        
        cur_genre = rl.GENRES_REVERSE.get(target_band['genre']) if target_band else rl.GENRES_LIST[0]
        b_genre = st.selectbox("Жанр*", rl.GENRES_LIST, index=rl.GENRES_LIST.index(cur_genre))
        b_date = st.date_input("Дата основания", value=target_band['founded_date'] if target_band else date.today())
        
        col1, col2 = st.columns(2)
        submit_button = col1.form_submit_button("Сохранить", type="primary")

        if is_edit:
            delete_button = col2.form_submit_button("❌ Удалить коллектив", type="secondary")
        
        if submit_button:
            if not b_name:
                st.error("Ошибка: Введите название")
            else:
                genre_code = rl.GENRES[b_genre]
                if target_band:
                    sql = "UPDATE bands SET band_name=%s, genre=%s, founded_date=%s WHERE band_id=%s"
                    args = (b_name, genre_code, b_date, target_band['band_id'])
                    action = "обновлен"
                else:
                    sql = "INSERT INTO bands (band_name, genre, founded_date) VALUES (%s, %s, %s)"
                    args = (b_name, genre_code, b_date)
                    action = "создан"
                
                if rl.execute_non_query(sql, args):
                    st.toast(f"✅ Коллектив {b_name} {action}!", icon="🎸")
                    load_bands.clear()
                    time.sleep(0.5)
                    st.rerun()

        if is_edit and delete_button:
            band_id = target_band['band_id']
            # Удаляем зависимости явно, так как универсальная функция не обрабатывает CASCADE
            rl.execute_non_query("DELETE FROM performances WHERE band_id=%s", (band_id,))
            rl.execute_non_query("DELETE FROM rehearsals WHERE band_id=%s", (band_id,))
            rl.execute_non_query("DELETE FROM band_membership WHERE band_id=%s", (band_id,))
            
            # Удаляем коллектив, используя универсальную функцию
            if rl.delete_record('bands', 'band_id', band_id):
                st.toast(f"✅ Коллектив {target_band['band_name']} удален!", icon="🗑️")
                load_bands.clear()
                time.sleep(0.5)
                st.rerun()

with tab3:
    if bands:
        s_band = st.selectbox("Управление составом", list(bands_map.keys()), key="mem_sel")
        bid = bands_map[s_band]
        
        st.markdown("##### Текущий состав")
        members = load_band_members(bid)
        
        if members:
            for m in members:
                col1, col2 = st.columns([4, 1])
                col1.write(f"👤 **{m['last_name']} {m['first_name']}** ({m['instrument_display']})")
                
                if col2.button("❌", key=f"del_{m['musician_id']}"):
                    # Удаляем членство
                    if rl.execute_non_query("DELETE FROM band_membership WHERE band_id=%s AND musician_id=%s", (bid, m['musician_id'])):
                        st.toast(f"Участник {m['last_name']} удален.", icon="👋")
                        load_band_members.clear()
                        time.sleep(0.5)
                        st.rerun()
        else:
            st.info("В коллективе пока нет участников.")

        st.divider()
        st.markdown("##### Добавить участника:")
        
        available = load_available_musicians(bid)
        
        if available:
            musician_options = {f"{m['last_name']} {m['first_name'] or ''} ({rl.INSTRUMENTS_REVERSE.get(m['instrument'], m['instrument'])})": m['musician_id'] for m in available}
            
            with st.form("add_member"):
                selected_musician = st.selectbox("Выберите музыканта", list(musician_options.keys()))
                
                if st.form_submit_button("Добавить в коллектив", type="primary"):
                    musician_id = musician_options[selected_musician]
                    query = "INSERT INTO band_membership (band_id, musician_id) VALUES (%s, %s)"
                    
                    if rl.execute_non_query(query, (bid, musician_id)):
                        st.toast("✅ Музыкант добавлен!", icon="➕")
                        load_band_members.clear()
                        time.sleep(0.5)
                        st.rerun()
        else:
            st.info("Нет доступных музыкантов для добавления")