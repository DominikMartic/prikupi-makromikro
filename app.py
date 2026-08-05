import streamlit as st
import pandas as pd
from datetime import datetime
import io
import html
import os
import qrcode
from supabase import create_client, Client
from streamlit_qrcode_scanner import qrcode_scanner

# ReportLab za profesionalni PDF izradu
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image

st.set_page_config(page_title="Makromikro - Mobilni Hub", layout="wide", page_icon="📦")

# === PODACI ZA KONEKCIJU ===
SUPABASE_URL = "https://mxirprzgxtiwyhrmkyxv.supabase.co".strip()
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im14aXJwcnpneHRpd3locm1reXh2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODU3ODQ4ODAsImV4cCI6MjEwMTM2MDg4MH0.6RSbGJ3T89rUY_tFBnv5QvQspNY_7FakipZWvdiEbpg".strip()

APP_URL = "https://prikupi-makromikro.streamlit.app" 

def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    supabase = init_supabase()
except Exception as e:
    supabase = None

# --- SPREMANJE I UCITAVANJE IZ BAZE ---
def ucitaj_naloge():
    if supabase:
        try:
            response = supabase.table("nalozi").select("*").order("created_at", desc=False).execute()
            raw_data = response.data
            nalozi = []
            for r in raw_data:
                nalozi.append({
                    "ID Naloga": r.get("id", "-"),
                    "Tip": r.get("tip", "-"),
                    "Komercijalist": r.get("komercijalist", "-"),
                    "Datum Prikupa": r.get("datum_prikupa", "-"),
                    "Dobavljac": r.get("dobavljac", "-"),
                    "Kontakt": r.get("kontakt", "-"),
                    "Adresa Prikupa": r.get("adresa_prikupa", "-"),
                    "Adresa Dostave": r.get("adresa_dostave", "-"),
                    "Opis robe": r.get("opis_robe", "-"),
                    "Napomena": r.get("napomena", "-"),
                    "Status": r.get("status", "-"),
                    "Vrijeme Obrade": r.get("vrijeme_obrade", "-"),
                    "Datum Kreiranja": r.get("created_at", "-")
                })
            return nalozi
        except Exception as e:
            st.error(f"Greška pri čitanju naloga iz baze: {e}")
            return []
    return []

def ucitaj_dobavljace():
    if supabase:
        try:
            response = supabase.table("dobavljaci").select("*").order("naziv", desc=False).execute()
            data = response.data
            return {d["naziv"]: d for d in data}
        except Exception:
            return {}
    return {}

def spremi_ili_azuriraj_dobavljaca(naziv, kontakt, adresa, napomena):
    if supabase and naziv and naziv != "Novi dobavljac...":
        try:
            podaci = {
                "naziv": naziv.strip(),
                "kontakt": kontakt.strip() if kontakt else "-",
                "adresa_prikupa": adresa.strip() if adresa else "-",
                "napomena": napomena.strip() if napomena else "-"
            }
            supabase.table("dobavljaci").upsert(podaci, on_conflict="naziv").execute()
        except Exception as e:
            print(f"Greska dobavljac: {e}")

def spremi_novi_nalog(n):
    if supabase:
        try:
            data = {
                "id": n["ID Naloga"],
                "tip": n["Tip"],
                "komercijalist": n["Komercijalist"],
                "datum_prikupa": n["Datum Prikupa"],
                "dobavljac": n["Dobavljac"],
                "kontakt": n["Kontakt"],
                "adresa_prikupa": n["Adresa Prikupa"],
                "adresa_dostave": n["Adresa Dostave"],
                "opis_robe": n["Opis robe"],
                "napomena": n["Napomena"],
                "status": n["Status"],
                "vrijeme_obrade": n["Vrijeme Obrade"]
            }
            supabase.table("nalozi").insert(data).execute()
            spremi_ili_azuriraj_dobavljaca(n["Dobavljac"], n["Kontakt"], n["Adresa Prikupa"], n["Napomena"])
        except Exception as e:
            st.error(f"Greska pri spremanju u bazu: {e}")

def azuriraj_status_naloga(id_naloga, novi_status, vrijeme_obrade="-"):
    if supabase:
        try:
            supabase.table("nalozi").update({
                "status": novi_status,
                "vrijeme_obrade": vrijeme_obrade
            }).eq("id", id_naloga).execute()
        except Exception as e:
            st.error(f"Greska pri azuriranju: {e}")

# Inicijalizacija sesije
if "baza_naloga" not in st.session_state:
    st.session_state.baza_naloga = ucitaj_naloge()

if "baza_dobavljaca" not in st.session_state:
    st.session_state.baza_dobavljaca = ucitaj_dobavljace()

if "user_role" not in st.session_state:
    st.session_state.user_role = "vozac"

if "ponovi_prikup_data" not in st.session_state:
    st.session_state.ponovi_prikup_data = None

if "scanned_id" not in st.session_state:
    st.session_state.scanned_id = None

query_params = st.query_params
if "role" in query_params:
    st.session_state.user_role = query_params.get("role")
if "search" in query_params:
    st.session_state.scanned_id = query_params.get("search")

st.markdown("""
    <style>
    .block-container { padding-top: 1.5rem; padding-bottom: 3rem; max-width: 900px; }
    .ai-header-box { display: flex; align-items: center; justify-content: space-between; background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); padding: 14px 20px; border-radius: 12px; color: white; margin-bottom: 15px; }
    </style>
""", unsafe_allow_html=True)

if st.session_state.user_role == "admin":
    role_display = "ADMINISTRATOR"
elif st.session_state.user_role == "komercijala":
    role_display = "KOMERCIJALA (Samo unos i pregled)"
else:
    role_display = "VOZAČ / TEREN"

st.markdown(f"""
    <div class="ai-header-box">
        <div>
            <h3 style="margin:0; font-size: 1.2rem; font-weight: 700; color: #ffffff;">⚡ Makromikro Hub</h3>
            <p style="margin:0; font-size: 0.75rem; color: #94a3b8;">Režim rada: {role_display}</p>
        </div>
    </div>
""", unsafe_allow_html=True)

if st.session_state.user_role in ["admin", "komercijala"]:
    col_top_btn1, col_top_btn2 = st.columns([4, 1.2])
    with col_top_btn2:
        if st.button("🔒 Odjava", use_container_width=True):
            st.session_state.user_role = "vozac"
            st.session_state.scanned_id = None
            st.query_params.clear()
            st.rerun()

def nadji_logo():
    for f in ["logo.png", "logo.jpg", "logo.jpeg", "LOGO.PNG"]:
        if os.path.exists(f):
            return f
    return None

def clean_txt(text):
    if not text:
        return "-"
    return html.escape(str(text)).replace('\n', '<br/>')

def generiraj_qr_sliku(sadrzaj):
    qr = qrcode.QRCode(box_size=2, border=1)
    qr.add_data(sadrzaj)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

def generiraj_pdf_makromikro(nalozi_list):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=35, leftMargin=35, topMargin=35, bottomMargin=35)
    story = []
    styles = getSampleStyleSheet()
    doc_title = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=15, fontName='Helvetica-Bold', textColor=colors.HexColor('#003366'))
    lbl_style = ParagraphStyle('Lbl', parent=styles['Normal'], fontSize=11, fontName='Helvetica-Bold', leading=15)
    val_style = ParagraphStyle('Val', parent=styles['Normal'], fontSize=11, fontName='Helvetica', leading=15)
    sec_hdr = ParagraphStyle('SecHdr', parent=styles['Normal'], fontSize=11, fontName='Helvetica-Bold', textColor=colors.HexColor('#003366'))

    putanja_loga = nadji_logo()
    aktivni_nalozi = [n for n in nalozi_list if n['Status'] != 'Storno']

    for idx, n in enumerate(aktivni_nalozi):
        if putanja_loga:
            try:
                logo_element = Image(putanja_loga, width=525, height=70)
                logo_element.hAlign = 'CENTER'
                story.append(logo_element)
                story.append(Spacer(1, 10))
            except Exception:
                pass

        naslov_tekst = f"ZAHTJEV ZA TRANSPORT — {clean_txt(n['Tip']).upper()} ({clean_txt(n['ID Naloga'])})"
        p_naslov = Paragraph(naslov_tekst, doc_title)
        
        try:
            qr_buf = generiraj_qr_sliku(str(n['ID Naloga']))
            qr_img = Image(qr_buf, width=45, height=45)
            qr_img.hAlign = 'RIGHT'
        except Exception:
            qr_img = Paragraph("", val_style)

        t_zaglavlje = Table([[p_naslov, qr_img]], colWidths=[470, 55])
        story.append(t_zaglavlje)

        podaci = [
            [Paragraph("Podnositelj zahtjeva:", lbl_style), Paragraph(clean_txt(n['Komercijalist']), val_style)],
            [Paragraph("Datum i vrijeme:", lbl_style), Paragraph(clean_txt(n['Datum Prikupa']), val_style)],
            [Paragraph("Dobavljač / Kontakt:", lbl_style), Paragraph(f"<b>{clean_txt(n['Dobavljac'])}</b> ({clean_txt(n['Kontakt'])})", val_style)],
            [Paragraph("Adresa prikupljanja:", lbl_style), Paragraph(clean_txt(n['Adresa Prikupa']), val_style)],
            [Paragraph("Adresa dostave:", lbl_style), Paragraph(clean_txt(n['Adresa Dostave']), val_style)],
            [Paragraph("Vrsta robe / Opis:", lbl_style), Paragraph(clean_txt(n['Opis robe']), val_style)],
            [Paragraph("Napomena za vozača:", lbl_style), Paragraph(clean_txt(n['Napomena']), val_style)],
        ]
        t_podaci = Table(podaci, colWidths=[160, 365])
        t_podaci.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
            ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f4f6f8')),
            ('PADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(t_podaci)
        story.append(Spacer(1, 15))

        story.append(Paragraph("- ispunjava vozač", sec_hdr))
        story.append(Spacer(1, 4))
        t_vozac = Table([
            [Paragraph("Prijevoz izvršio (ime i prezime):", val_style), Paragraph("Datum:", val_style), Paragraph("Potpis:", val_style)],
            ["\n\n", "", ""]
        ], colWidths=[240, 140, 145])
        t_vozac.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#aaaaaa')), ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e9ecef')), ('PADDING', (0,0), (-1,-1), 6)]))
        story.append(t_vozac)
        story.append(Spacer(1, 15))

        story.append(Paragraph("- ispunjava skladištar", sec_hdr))
        story.append(Spacer(1, 4))
        t_skladiste = Table([
            [Paragraph("Robu preuzeo i kontrolirao:", val_style), Paragraph("Datum:", val_style), Paragraph("Potpis:", val_style)],
            ["\n\n", "", ""]
        ], colWidths=[240, 140, 145])
        t_skladiste.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#aaaaaa')), ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e9ecef')), ('PADDING', (0,0), (-1,-1), 6)]))
        story.append(t_skladiste)

        if idx < len(aktivni_nalozi) - 1:
            story.append(PageBreak())

    doc.build(story)
    buffer.seek(0)
    return buffer

# --- VOZAČ / TERENSKI MOD ---
if st.session_state.user_role == "vozac":
    st.subheader("🚚 Terenski Mod - Preuzimanje Naloga")
    st.caption("Skenirajte QR kod kamerom uređaja ili upišite ID naloga:")

    scanned_qr = qrcode_scanner(key='qr_scanner')
    if scanned_qr:
        st.session_state.scanned_id = scanned_qr

    with st.container(border=True):
        search_query = st.text_input("🔍 Pretraga / ID naloga:", value=st.session_state.scanned_id or "")

    filtrirani = st.session_state.baza_naloga
    if search_query:
        sq = search_query.lower().strip()
        filtrirani = [x for x in filtrirani if sq in x["ID Naloga"].lower() or sq in x["Dobavljac"].lower() or sq in x["Opis robe"].lower()]

    if not search_query:
        st.info("ℹ️ Skenirajte QR kod kamerom iznad ili upišite ID u polje za pretragu.")
    elif not filtrirani:
        st.warning("Nema pronađenih naloga za zadani pojam.")
    else:
        for i, nalog in enumerate(filtrirani):
            with st.container(border=True):
                st.markdown(f"### 📄 {nalog['ID Naloga']} ({nalog['Tip']})")
                st.markdown(f"🕒 **Kreirano:** {nalog.get('Datum Kreiranja', '-')}")
                st.markdown(f"🏢 **Dobavljač:** {nalog['Dobavljac']}")
                st.markdown(f"📍 **Adresa prikupljanja:** {nalog['Adresa Prikupa']}")
                st.markdown(f"📦 **Opis robe:** {nalog['Opis robe']}")
                st.markdown(f"📞 **Kontakt:** {nalog['Kontakt']}")
                st.markdown(f"📌 **Napomena:** {nalog['Napomena']}")
                
                status_trenutni = nalog['Status']
                if status_trenutni == "Prikupljeno":
                    st.success(f"✅ Status: PREUZETO dana {nalog['Vrijeme Obrade']}")
                else:
                    st.info(f"⏳ Trenutni status: {status_trenutni}")
                    if st.button(f"✅ OZNAČI KAO PREUZETO ({nalog['ID Naloga']})", key=f"btn_prev_{nalog['ID Naloga']}_{i}", type="primary", use_container_width=True):
                        vrijeme_sada = datetime.now().strftime('%d.%m.%Y. %H:%M')
                        azuriraj_status_naloga(nalog['ID Naloga'], "Prikupljeno", vrijeme_sada)
                        st.session_state.baza_naloga = ucitaj_naloge()
                        st.success("Uspješno označeno kao preuzeto!")
                        st.rerun()

    st.markdown("<br><br><br>", unsafe_allow_html=True)
    with st.container(border=True):
        st.caption("🔐 Pristup sustavu za ovlaštene osobe")
        col_p1, col_p2 = st.columns(2)
        
        with col_p1:
            pass_kom = st.text_input("Lozinka - Komercijala:", type="password", key="p_kom")
            zapamti_kom = st.checkbox("Zapamti moju prijavu", key="zap_kom", value=True)
            if st.button("Prijava: Komercijala", use_container_width=True):
                if pass_kom == "komercijala123":
                    st.session_state.user_role = "komercijala"
                    if zapamti_kom:
                        st.query_params["role"] = "komercijala"
                    st.rerun()
                else:
                    st.error("Netočna lozinka!")

        with col_p2:
            pass_adm = st.text_input("Lozinka - Admin:", type="password", key="p_adm")
            zapamti_adm = st.checkbox("Zapamti moju prijavu", key="zap_adm", value=True)
            if st.button("Prijava: Admin", type="primary", use_container_width=True):
                if pass_adm == "admin123":
                    st.session_state.user_role = "admin"
                    if zapamti_adm:
                        st.query_params["role"] = "admin"
                    st.rerun()
                else:
                    st.error("Netočna lozinka!")

    st.stop()

# --- KOMERCIJALA ILI ADMIN MOD ---
tab1, tab2 = st.tabs(["✨ Unos Novog Naloga", "📊 Pregled & Upravljanje"])

with tab1:
    st.subheader("Unos novog naloga")
    pp_data = st.session_state.ponovi_prikup_data
    if pp_data:
        st.info(f"🔄 Učitani podaci za ponovljeni prikup iz naloga **{pp_data.get('ID Naloga', '')}**")

    dobavljaci_dict = st.session_state.baza_dobavljaca
    lista_dobavljaca = ["Novi dobavljac..."] + sorted(list(dobavljaci_dict.keys()))

    c_dob1, c_dob2 = st.columns([1, 1])
    default_dob_index = 0
    if pp_data and pp_data.get("Dobavljac") in lista_dobavljaca:
        default_dob_index = lista_dobavljaca.index(pp_data.get("Dobavljac"))

    odabrani_dobavljac_opcija = c_dob1.selectbox("Odaberi dobavljača:", lista_dobavljaca, index=default_dob_index)

    if odabrani_dobavljac_opcija != "Novi dobavljac...":
        podaci_dob = dobavljaci_dict.get(odabrani_dobavljac_opcija, {})
        zadati_naziv = odabrani_dobavljac_opcija
        zadati_kontakt = podaci_dob.get("kontakt", "")
        zadana_adresa = podaci_dob.get("adresa_prikupa", "")
        zadana_napomena = podaci_dob.get("napomena", "")
    else:
        zadati_naziv = pp_data.get("Dobavljac", "") if pp_data else ""
        zadati_kontakt = pp_data.get("Kontakt", "") if pp_data else ""
        zadana_adresa = pp_data.get("Adresa Prikupa", "") if pp_data else ""
        zadana_napomena = pp_data.get("Napomena", "") if pp_data else ""

    with st.container(border=True):
        with st.form("forma_unos", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            tip = c1.selectbox("Tip dokumenta", ["Prikup", "Povrat"])
            komercijalist = c2.text_input("Podnositelj zahtjeva", value=pp_data.get("Komercijalist", "") if pp_data else "")
            datum = c3.date_input("Datum prikupa", datetime.now())

            c4, c5 = st.columns(2)
            dobavljac = c4.text_input("Dobavljač", value=zadati_naziv)
            kontakt = c5.text_input("Kontakt telefon", value=zadati_kontakt)

            c6, c7 = st.columns(2)
            adresa_prikupa = c6.text_input("Adresa prikupljanja", value=zadana_adresa)
            adresa_dostave = c7.text_input("Adresa dostave", value="Makromikro grupa d.o.o., Vukomericka ulica 6, 10410 Velika Gorica")

            opis = st.text_area("Vrsta robe / Opis", value=pp_data.get("Opis robe", "") if pp_data else "")
            napomena = st.text_input("Napomena za vozača", value=zadana_napomena)

            submit = st.form_submit_button("Spremi Nalog", type="primary", use_container_width=True)

            if submit:
                if not komercijalist or not dobavljac or not adresa_prikupa or not opis:
                    st.error("Ispunite obavezna polja!")
                else:
                    broj = len(st.session_state.baza_naloga) + 1
                    prefiks = "PR" if tip == "Prikup" else "POV"
                    id_naloga = f"{prefiks}-2026-{broj:03d}"
                    
                    novi_nalog = {
                        "ID Naloga": id_naloga,
                        "Tip": tip,
                        "Komercijalist": komercijalist,
                        "Datum Prikupa": datum.strftime("%Y-%m-%d"),
                        "Dobavljac": dobavljac,
                        "Kontakt": kontakt or "-",
                        "Adresa Prikupa": adresa_prikupa,
                        "Adresa Dostave": adresa_dostave,
                        "Opis robe": opis,
                        "Napomena": napomena or "-",
                        "Status": "Na čekanju",
                        "Vrijeme Obrade": "-"
                    }
                    spremi_novi_nalog(novi_nalog)
                    st.session_state.baza_naloga = ucitaj_naloge()
                    st.session_state.baza_dobavljaca = ucitaj_dobavljace()
                    st.session_state.ponovi_prikup_data = None
                    st.success(f"Nalog {id_naloga} uspješno spremljen u bazu!")

with tab2:
    col_h1, col_h2 = st.columns([3, 1])
    col_h1.subheader("📋 Pregled & Upravljanje nalozima")
    if col_h2.button("🔄 Osvježi", use_container_width=True):
        st.session_state.baza_naloga = ucitaj_naloge()
        st.session_state.baza_dobavljaca = ucitaj_dobavljace()
        st.rerun()

    if not st.session_state.baza_naloga:
        st.info("Nema unesenih naloga u bazi.")
    else:
        with st.container(border=True):
            st.markdown("##### 🔎 Filteri pretrage")
            f_col1, f_col2, f_col3, f_col4, f_col5 = st.columns(5)

            search_query = f_col1.text_input("Pretraga (ID / opis):", value=st.session_state.scanned_id or "")
            
            svi_komercijalisti = ["Svi"] + sorted(list(set(n["Komercijalist"] for n in st.session_state.baza_naloga if n["Komercijalist"])))
            odabrani_komercijalist = f_col2.selectbox("Komercijalist:", svi_komercijalisti)

            svi_dobavljaci = ["Svi"] + sorted(list(set(n["Dobavljac"] for n in st.session_state.baza_naloga if n["Dobavljac"])))
            odabrani_dobavljac = f_col3.selectbox("Dobavljač:", svi_dobavljaci)

            svi_datumi = ["Svi"] + sorted(list(set(n["Datum Prikupa"] for n in st.session_state.baza_naloga if n["Datum Prikupa"])))
            odabrani_datum = f_col4.selectbox("Datum prikupa:", svi_datumi)

            svi_datumi_kreiranja = ["Svi"] + sorted(list(set(str(n.get("Datum Kreiranja", ""))[:10] for n in st.session_state.baza_naloga if n.get("Datum Kreiranja"))))
            odabrani_datum_kreiranja = f_col5.selectbox("Datum kreiranja:", svi_datumi_kreiranja)

        filtrirani = st.session_state.baza_naloga

        if search_query:
            sq = search_query.lower()
            filtrirani = [x for x in filtrirani if sq in x["ID Naloga"].lower() or sq in x["Dobavljac"].lower() or sq in x["Opis robe"].lower()]
        
        if odabrani_komercijalist != "Svi":
            filtrirani = [x for x in filtrirani if x["Komercijalist"] == odabrani_komercijalist]

        if odabrani_dobavljac != "Svi":
            filtrirani = [x for x in filtrirani if x["Dobavljac"] == odabrani_dobavljac]

        if odabrani_datum != "Svi":
            filtrirani = [x for x in filtrirani if x["Datum Prikupa"] == odabrani_datum]

        if odabrani_datum_kreiranja != "Svi":
            filtrirani = [x for x in filtrirani if str(x.get("Datum Kreiranja", ""))[:10] == odabrani_datum_kreiranja]

        ukupno_prikaza = len(filtrirani)
        broj_ceka_ispis = len([x for x in filtrirani if x["Status"] == "Na čekanju"])
        broj_isprintano = len([x for x in filtrirani if x["Status"] == "Isprintano"])
        broj_prikupljeno = len([x for x in filtrirani if x["Status"] == "Prikupljeno"])
        broj_storno = len([x for x in filtrirani if x["Status"] == "Storno"])

        st.markdown("---")
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("📊 Prikazano", ukupno_prikaza)
        m2.metric("⏳ Na čekanju", broj_ceka_ispis)
        m3.metric("🖨️ Isprintano", broj_isprintano)
        m4.metric("✅ Prikupljeno", broj_prikupljeno)
        m5.metric("❌ Storno", broj_storno)
        st.markdown("---")

        with st.container(border=True):
            st.markdown("##### 📈 Analitika i Izvoz podataka (Tjedno / Mjesečno / Godišnje)")
            ex_c1, ex_c2, ex_c3 = st.columns(3)
            
            period_izvoza = ex_c1.selectbox(
                "Odaberi period za analizu:",
                ["Svi prikazani nalozi", "Tekući tjedan", "Tekući mjesec", "Tekuća godina"]
            )

            nalozi_za_izvoz = filtrirani
            sadasnji_datum = datetime.now()

            if period_izvoza == "Tekući tjedan":
                pocetak_tjedna = (sadasnji_datum - pd.Timedelta(days=sadasnji_datum.weekday())).strftime('%Y-%m-%d')
                nalozi_za_izvoz = [n for n in filtrirani if str(n.get("Datum Kreiranja", ""))[:10] >= pocetak_tjedna]
            elif period_izvoza == "Tekući mjesec":
                trenutni_mjesec = sadasnji_datum.strftime('%Y-%m')
                nalozi_za_izvoz = [n for n in filtrirani if str(n.get("Datum Kreiranja", ""))[:7] == trenutni_mjesec]
            elif period_izvoza == "Tekuća godina":
                trenutna_godina = sadasnji_datum.strftime('%Y')
                nalozi_za_izvoz = [n for n in filtrirani if str(n.get("Datum Kreiranja", ""))[:4] == trenutna_godina]

            ex_c2.markdown(f"<br>Broj naloga za izvoz: **{len(nalozi_za_izvoz)}**", unsafe_allow_html=True)

            if nalozi_za_izvoz:
                df_export = pd.DataFrame(nalozi_za_izvoz)
                csv_data = df_export.to_csv(index=False).encode('utf-8-sig')

                ex_c3.download_button(
                    label="📥 Preuzmi Excel/CSV izvještaj",
                    data=csv_data,
                    file_name=f"Makromikro_Analiza_{period_izvoza.lower().replace(' ', '_')}_{datetime.now().strftime('%Y-%m-%d')}.csv",
                    mime="text/csv",
                    type="primary",
                    use_container_width=True
                )
            else:
                ex_c3.warning("Nema naloga za odabrani period.")

        st.markdown("---")

        za_print = [x for x in filtrirani if x["Status"] == "Na čekanju"]
        if za_print:
            pdf_bytes = generiraj_pdf_makromikro(za_print).getvalue()
            
            download_clicked = st.download_button(
                label=f"📄 Preuzmi PDF Zbirni Zahtjev ({len(za_print)} naloga)",
                data=pdf_bytes,
                file_name=f"Zahtjev_za_transport_{datetime.now().strftime('%Y-%m-%d')}.pdf",
                mime="application/pdf",
                type="primary"
            )
            
            if download_clicked:
                for nalog_za_azuriranje in za_print:
                    azuriraj_status_naloga(nalog_za_azuriranje["ID Naloga"], "Isprintano", "-")
                st.session_state.baza_naloga = ucitaj_naloge()
                st.rerun()

        statusi_opcije = ["Na čekanju", "Isprintano", "Prikupljeno", "Storno"]
        is_admin = (st.session_state.user_role == "admin")

        for i, nalog in enumerate(filtrirani):
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([1.2, 1.8, 2.5, 1.5, 2.2])
                c1.markdown(f"**{nalog['ID Naloga']}**<br>Prikup: _{nalog['Datum Prikupa']}_<br><span style='font-size:0.75rem; color:gray;'>Kreirano: {nalog.get('Datum Kreiranja', '-')}</span>", unsafe_allow_html=True)
                c2.markdown(f"👤 **{nalog['Komercijalist']}**")
                c3.markdown(f"🏢 **{nalog['Dobavljac']}**<br>_{nalog['Adresa Prikupa']}_", unsafe_allow_html=True)
                c4.markdown(f"**{nalog['Status']}**")

                with c5:
                    if is_admin:
                        novi_status = st.selectbox("Status", statusi_opcije, index=statusi_opcije.index(nalog['Status']) if nalog['Status'] in statusi_opcije else 0, key=f"st_{nalog['ID Naloga']}_{i}", label_visibility="collapsed")
                        if novi_status != nalog['Status']:
                            vrijeme = f"{datetime.now().strftime('%d.%m.%Y. %H:%M')}" if novi_status == "Prikupljeno" else "-"
                            azuriraj_status_naloga(nalog['ID Naloga'], novi_status, vrijeme)
                            st.session_state.baza_naloga = ucitaj_naloge()
                            st.rerun()
                    else:
                        st.caption(f"Vrijeme obrade: {nalog['Vrijeme Obrade']}")

                    sub_c1, sub_c2 = st.columns(2)
                    single_pdf = generiraj_pdf_makromikro([nalog]).getvalue()
                    sub_c1.download_button("📄 PDF", single_pdf, file_name=f"Nalog_{nalog['ID Naloga']}.pdf", mime="application/pdf", key=f>
                    if sub_c2.button("🔄 Ponovi", key=f"r_{nalog['ID Naloga']}_{i}", use_container_width=True):
                        st.session_state.ponovi_prikup_data = nalog
                        st.rerun()
