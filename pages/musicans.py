import streamlit as st
import rac_lib as rl
import pandas as pd
import re
import time # Для задержки при toast

st.set_page_config(page_title="Музыканты", page_icon="🎵", layout="wide")
rl.sidebar_pg()
st.title("🎵 Музыканты")

# --- Логика ---
def validate_phone(phone):
    # Формат: +375XXXXXXXXX
    return bool(re.match(r'^\+375[0-9]{9}$', phone))

@st.cache_data(ttl=60)
def load_musicians():
    query = """
        SELECT musician_id, first_name, last_name, instrument, phone, telegram
        FROM musicians 
        ORDER BY last_name, first_name
    """
    data = rl.run_query(query)
    
    for m in data:
        m['instrument_display'] = rl.INSTRUMENTS_REVERSE.get(m['instrument'], m['instrument'])
        m['display_name'] = f"{m['last_name']} {m['first_name'] or ''}"
    return data

if 'musicians_data' not in st.session_state:
    st.session_state.musicians_data = load_musicians()

data = st.session_state.musicians_data
df = pd.DataFrame(data)

tab1, tab2, tab3 = st.tabs(["Список", "Добавить", "Управление"])

with tab1:
    if not df.empty:
        df_show = df.copy()
        
        search = st.text_input("🔍 Поиск", placeholder="Имя, фамилия или телефон...")
        if search:
            mask = df_show.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
            df_show = df_show[mask]
            
        st.dataframe(
            df_show[['last_name', 'first_name', 'instrument_display', 'phone', 'telegram']]
            .rename(columns={'last_name': 'Фамилия', 'first_name': 'Имя', 'instrument_display': 'Инструмент', 'phone': 'Телефон'}),
            use_container_width=True, hide_index=True
        )
    else:
        st.info("Список пуст")

with tab2:
    with st.form("add_musician"):
        st.markdown("##### Добавление нового музыканта")
        c1, c2 = st.columns(2)
        f_name = c1.text_input("Имя")
        l_name = c1.text_input("Фамилия*")
        inst = c2.selectbox("Инструмент*", rl.INSTRUMENTS_LIST)
        phone = c2.text_input("Телефон*", value="+375", help="Формат: +375XXXXXXXXX")
        tg = st.text_input("Telegram (@user)")
        
        if st.form_submit_button("Сохранить", type="primary"):
            if not l_name or not validate_phone(phone):
                st.error("Ошибка: Проверьте фамилию и формат телефона (+375...)")
            else:
                sql = """INSERT INTO musicians (first_name, last_name, instrument, phone, telegram) 
                         VALUES (%s, %s, %s, %s, %s)"""
                if rl.execute_non_query(sql, (f_name, l_name, rl.INSTRUMENTS[inst], phone, tg)):
                    st.toast("✅ Музыкант добавлен!", icon="🎵"); 
                    load_musicians.clear() 
                    time.sleep(0.5)
                    st.rerun()

with tab3:
    st.markdown("### Редактирование и удаление")
    if not df.empty:
        musician_options = {m['display_name']: m['musician_id'] for m in data}
        sel_name = st.selectbox("Выберите музыканта", list(musician_options.keys()), key="edit_sel")
        sel_row = next(r for r in data if r['musician_id'] == musician_options[sel_name])
        
        c1, c2 = st.columns(2)
        
        # --- БЛОК РЕДАКТИРОВАНИЯ ---
        with c1.form("edit_form"):
            st.caption("Редактирование данных")
            cur_inst_key = rl.INSTRUMENTS_REVERSE.get(sel_row['instrument'])
            n_inst = st.selectbox("Инструмент", rl.INSTRUMENTS_LIST, 
                                  index=rl.INSTRUMENTS_LIST.index(cur_inst_key) if cur_inst_key in rl.INSTRUMENTS_LIST else 0)
            n_phone = st.text_input("Телефон", sel_row['phone'])
            n_tg = st.text_input("Telegram", sel_row['telegram'] or '')

            if st.form_submit_button("Обновить", type="primary"):
                if validate_phone(n_phone):
                    rl.execute_non_query(
                        "UPDATE musicians SET phone=%s, instrument=%s, telegram=%s WHERE musician_id=%s",
                        (n_phone, rl.INSTRUMENTS[n_inst], n_tg, sel_row['musician_id'])
                    )
                    st.toast("✅ Обновлено!", icon="📝"); 
                    load_musicians.clear()
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Неверный формат телефона")
        
        # --- БЛОК УДАЛЕНИЯ ---
        with c2.form("delete_form"):
            st.caption("Осторожно, удаление!")
            st.warning("Удаление музыканта автоматически удалит его из всех коллективов.")
            
            if st.form_submit_button("Удалить музыканта", type="primary"):
                musician_id = sel_row['musician_id']
                
                # 1. Удаляем зависимости (членство)
                rl.delete_record("band_membership", "musician_id", musician_id)
                
                # 2. Удаляем самого музыканта, используя универсальную функцию
                if rl.delete_record("musicians", "musician_id", musician_id):
                    st.toast("✅ Музыкант удален!", icon="🗑️"); 
                    load_musicians.clear()
                    time.sleep(0.5)
                    st.rerun()
    else:
        st.info("Нет данных для управления.")