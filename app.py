import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Makromikro - Prikupi & Povrati", layout="wide", page_icon="📦")

# Naslov
st.title("📦 MAKROMIKRO GRUPA - Sustav za Prikup i Povrat Robe")

# Baza u memoriji
if "baza_naloga" not in st.session_state:
    st.session_state.baza_naloga = []

# 1. FORMA ZA UNOS
st.header("1. Unos novog naloga (Komercijalisti)")
with st.form("forma_unos", clear_on_submit=True):
    col1, col2, col3 = st.columns(3)
    tip = col1.selectbox("Tip dokumenta", ["Prikup", "Povrat"])
    komercijalist = col2.text_input("Komercijalist (Ime)")
    datum = col3.date_input("Datum prikupa", datetime.now())

    col4, col5 = st.columns(2)
    dobavljac = col4.text_input("Dobavljač")
    adresa = col5.text_input("Adresa i kontakt")

    opis = st.text_area("Opis robe / Stavke (Količina, palete, artikli)")
    napomena = st.text_input("Napomena za vozača")

    spremi = st.form_submit_button("Spremi Nalog", type="primary")

    if spremi:
        if not komercijalist or not dobavljac or not opis:
            st.error("Molimo ispunite Ime, Dobavljača i Opis robe!")
        else:
            broj = len(st.session_state.baza_naloga) + 1
            prefiks = "PR" if tip == "Prikup" else "POV"
            id_naloga = f"{prefiks}-2026-{broj:03d}"
            
            st.session_state.baza_naloga.append({
                "ID Naloga": id_naloga,
                "Tip": tip,
                "Komercijalist": komercijalist,
                "Datum Prikupa": datum.strftime("%Y-%m-%d"),
                "Dobavljač": dobavljac,
                "Adresa i Kontakt": adresa,
                "Opis robe": opis,
                "Napomena": napomena,
                "Status": "Na čekanju",
                "Vrijeme Obrade": "-"
            })
            st.success(f"Uspješno spremljen nalog {id_naloga}!")

st.divider()

# 2. TABLICA I AKCIJE
st.header("2. Pregled i Obrada Naloga (Logistika)")

if st.session_state.baza_naloga:
    df = pd.DataFrame(st.session_state.baza_naloga)
    st.dataframe(df, use_container_width=True)

    col_btn1, col_btn2 = st.columns(2)

    if col_btn1.button("✅ Označi DANAŠNJE naloge kao PRIKUPLJENO", type="secondary"):
        danas_str = datetime.now().strftime("%Y-%m-%d")
        sada_str = datetime.now().strftime("%d.%m.%Y. %H:%M")
        brojac = 0
        for item in st.session_state.baza_naloga:
            if item["Datum Prikupa"] == danas_str and item["Status"] == "Na čekanju":
                item["Status"] = "Prikupljeno"
                item["Vrijeme Obrade"] = sada_str
                brojac += 1
        st.success(f"Promijenjen status u 'Prikupljeno' za {brojac} naloga!")
        st.rerun()

    if col_btn2.button("🖨️ Pripremi A4 naloge za ISPIS"):
        danas_str = datetime.now().strftime("%Y-%m-%d")
        nalozi_danas = [x for x in st.session_state.baza_naloga if x["Datum Prikupa"] == danas_str and x["Status"] == "Na čekanju"]

        if not nalozi_danas:
            st.warning("Nema naloga za današnji datum koji su 'Na čekanju'!")
        else:
            st.subheader("Ispis naloga (Pritisnite Ctrl+P u pregledniku za print na A4)")
            for n in nalozi_danas:
                st.markdown(f"""
                ---
                ### MAKROMIKRO GRUPA d.o.o.
                **NALOG ZA {n['Tip'].upper()} ROBE - {n['ID Naloga']}**
                * **Datum prikupa:** {n['Datum Prikupa']} | **Komercijalist:** {n['Komercijalist']}
                * **Dobavljač:** {n['Dobavljač']}
                * **Adresa i kontakt:** {n['Adresa i Kontakt']}
                * **Napomena:** {n['Napomena']}

                **OPIS ROBE / STAVKE:**
                > {n['Opis robe']}

                \n\n
                Potpis vozača / skladišta: _________________ &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Potpis i pečat dobavljača: _________________
                ---
                """)
else:
    st.info("Trenutno nema unesenih naloga.")
