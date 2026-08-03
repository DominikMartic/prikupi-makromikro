import streamlit as st
import pandas as pd
from datetime import datetime
import io
import html
import os
import qrcode
from supabase import create_client, Client

# ReportLab za profesionalni PDF izgled
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image

st.set_page_config(page_title="Makromikro - AI Operations Hub", layout="wide", page_icon="📦")

# === PODACI ZA KONEKCIJU NA SUPABASE BAZU ===
SUPABASE_URL = "https://mxirprzgxtiwyhrmkyxv.supabase.co".strip()
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im14aXJwcnpneHRpd3locm1reXh2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODU3ODQ4ODAsImV4cCI6MjEwMTM2MDg4MH0.6RSbGJ3T89rUY_tFBnv5QvQspNY_7FakipZWvdiEbpg".strip()

def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    supabase = init_supabase()
except Exception as e:
    supabase = None

# --- SPREMANJE I UCITAVANJE IZ TRAJNE BAZE ---
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
                    "Vrijeme Obrade": r.get("vrijeme_obrade", "-")
                })
            return nalozi
        except Exception:
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
            st.error(f"Greska pri spremanju dobavljaca: {e}")

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

def obrisi_sve_naloge():
    if supabase:
        try:
            supabase.table("nalozi").delete().neq("id", "NEPOSTOJECI_ID").execute()
        except Exception as e:
            st.error(f"Greska pri brisanju naloga: {e}")

def obrisi_sve_dobavljace():
    if supabase:
        try:
            supabase.table("dobavljaci").delete().neq("naziv", "NEPOSTOJECI_NAZIV").execute()
        except Exception as e:
            st.error(f"Greska pri brisanju dobavljaca: {e}")

# Inicijalizacija sesije
if "baza_naloga" not in st.session_state:
    st.session_state.baza_naloga = ucitaj_naloge()

if "baza_dobavljaca" not in st.session_state:
    st.session_state.baza_dobavljaca = ucitaj_dobavljace()

if "is_logged_in" not in st.session_state:
    st.session_state.is_logged_in = False

if "user_role" not in st.session_state:
    st.session_state.user_role = None

if "ponovi_prikup_data" not in st.session_state:
    st.session_state.ponovi_prikup_data = None

query_params = st.query_params
if not st.session_state.is_logged_in and "role" in query_params:
    st.session_state.is_logged_in = True
    st.session_state.user_role = query_params["role"]

# --- MODERNI AI / SAAS CSS STILOVI ---
st.markdown("""
    <style>
    .block-container { padding-top: 2rem; padding-bottom: 3rem; }
    
    .ai-badge-cekanje { background: rgba(245, 158, 11, 0.1); color: #d97706; border: 1px solid rgba(245, 158, 11, 0.2); padding: 4px 10px; border-radius: 20px; font-weight: 600; font-size: 0.75rem; }
    .ai-badge-isprintano { background: rgba(14, 165, 233, 0.1); color: #0284c7; border: 1px solid rgba(14, 165, 233, 0.2); padding: 4px 10px; border-radius: 20px; font-weight: 600; font-size: 0.75rem; }
    .ai-badge-prikupljeno { background: rgba(34, 197, 94, 0.1); color: #16a34a; border: 1px solid rgba(34, 197, 94, 0.2); padding: 4px 10px; border-radius: 20px; font-weight: 600; font-size: 0.75rem; }
    .ai-badge-storno { background: rgba(239, 68, 68, 0.1); color: #dc2626; border: 1px solid rgba(239, 68, 68, 0.2); padding: 4px 10px; border-radius: 20px; font-weight: 600; font-size: 0.75rem; text-decoration: line-through; }

    .ai-header-box {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        padding: 16px 24px;
        border-radius: 12px;
        color: white;
        margin-bottom: 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    }
    </style>
""", unsafe_allow_html=True)

# --- SUSTAV ZA PRIJAVU ---
if not st.session_state.is_logged_in:
    c_l1, c_l2, c_l3 = st.columns([1, 1.2, 1])
    with c_l2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("### ✨ Makromikro AI Hub")
            st.caption("Prijavite se za pristup sustavu transportnih naloga")
            unesena_lozinka = st.text_input("Pristupna lozinka:", type="password")
            zapamti_me = st.checkbox("Zapamti me na ovom uredaju")
            
            if st.button("Pokreni aplikaciju", type="primary", use_container_width=True):
                 odabrana_uloga = None
                 if unesena_lozinka == "admin123":
                     odabrana_uloga = "admin"
                 elif unesena_lozinka == "komercijalist123":
                     odabrana_uloga = "komercijalist"
                     
                 if odabrana_uloga:
                     st.session_state.is_logged_in = True
                     st.session_state.user_role = odabrana_uloga
                     if zapamti_me:
                         st.query_params["role"] = odabrana_uloga
                     st.rerun()
                 else:
                     st.error("Pogresna lozinka!")
    st.stop()

# --- GLAVNI DIO APLIKACIJE ---
role_display = st.session_state.user_role.upper()
st.markdown(f"""
    <div class="ai-header-box">
        <div>
            <h2 style="margin:0; font-size: 1.4rem; font-weight: 700; color: #ffffff;">⚡ Makromikro Operations Hub</h2>
            <p style="margin:0; font-size: 0.85rem; color: #94a3b8;">Inteligentno upravljanje prikupima, povratima i WMS logistikom</p>
        </div>
        <div style="background: rgba(255,255,255,0.1); padding: 6px 14px; border-radius: 20px; font-size: 0.85rem; font-weight: 600; color: #38bdf8;">
            Uloga: {role_display}
        </div>
    </div>
""", unsafe_allow_html=True)

if st.button("🔒 Odjava iz sustava", use_container_width=False):
    st.session_state.is_logged_in = False
    st.session_state.user_role = None
    st.session_state.ponovi_prikup_data = None
    if "role" in st.query_params:
        del st.query_params["role"]
    st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

def nadji_logo():
    moguce_opcije = ["logo.png", "logo.jpg", "logo.jpeg", "logo.PNG", "LOGO.PNG", "LOGO.JPG"]
    for f in moguce_opcije:
        if os.path.exists(f):
            return f
    return None

def clean_txt(text):
    if not text:
        return "-"
    escaped = html.escape(str(text))
    return escaped.replace('\n', '<br/>')

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
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=35, leftMargin=35, topMargin=35, bottomMargin=35
    )
    story = []
    styles = getSampleStyleSheet()

    doc_title = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=15, fontName='Helvetica-Bold', textColor=colors.HexColor('#003366'))
    
    lbl_style = ParagraphStyle('Lbl', parent=styles['Normal'], fontSize=11, fontName='Helvetica-Bold', leading=15)
    val_style = ParagraphStyle('Val', parent=styles['Normal'], fontSize=11, fontName='Helvetica', leading=15)
    sec_hdr = ParagraphStyle('SecHdr', parent=styles['Normal'], fontSize=11, fontName='Helvetica-Bold', textColor=colors.HexColor('#003366'))

    putanja_loga = nadji_logo()
    aktivni_nalozi = [n for n in nalozi_list if n['Status'] != 'Storno']

    for idx, n in enumerate(aktivni_nalozi):
        # Logo na vrhu (ako postoji)
        if putanja_loga:
            try:
                logo_element = Image(putanja_loga, width=525, height=70)
                logo_element.hAlign = 'CENTER'
                story.append(logo_element)
                story.append(Spacer(1, 10))
            except Exception:
                pass

        # Naslov i QR kod smješteni u tablicu da budu u istoj liniji (naslov lijevo, QR kod desno)
        id_naloga_txt = clean_txt(n['ID Naloga'])
        naslov_tekst = f"ZAHTJEV ZA TRANSPORT — {clean_txt(n['Tip']).upper()} ({id_naloga_txt})"
        p_naslov = Paragraph(naslov_tekst, doc_title)

        # Generiranje QR koda za ovaj specifični nalog
        try:
            qr_buf = generiraj_qr_sliku(id_naloga_txt)
            qr_img = Image(qr_buf, width=45, height=45)
            qr_img.hAlign = 'RIGHT'
        except Exception:
            qr_img = Paragraph("", val_style)

        t_zaglavlje = Table([[p_naslov, qr_img]], colWidths=[470, 55])
        t_zaglavlje.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (1,0), (1,0), 'RIGHT'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ]))
        story.append(t_zaglavlje)

        podaci = [
            [Paragraph("Podnositelj zahtjeva:", lbl_style), Paragraph(clean_txt(n['Komercijalist']), val_style)],
            [Paragraph("Datum i vrijeme:", lbl_style), Paragraph(clean_txt(n['Datum Prikupa']), val_style)],
            [Paragraph("Dobavljac / Kontakt:", lbl_style), Paragraph(f"<b>{clean_txt(n['Dobavljac'])}</b> ({clean_txt(n['Kontakt'])})", val_style)],
            [Paragraph("Adresa prikupljanja:", lbl_style), Paragraph(clean_txt(n['Adresa Prikupa']), val_style)],
            [Paragraph("Adresa dostave (Mjesto otpreme):", lbl_style), Paragraph(clean_txt(n['Adresa Dostave']), val_style)],
            [Paragraph("Vrsta robe / Opis:", lbl_style), Paragraph(clean_txt(n['Opis robe']), val_style)],
            [Paragraph("Napomena za vozaca:", lbl_style), Paragraph(clean_txt(n['Napomena']), val_style)],
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

        story.append(Paragraph("- ispunjava vozac", sec_hdr))
        story.append(Spacer(1, 4))
        
        vozac_data = [
            [Paragraph("Prijevoz je izvrsio (ime i prezime vozaca):", val_style), Paragraph("Datum:", val_style), Paragraph("Potpis:", val_style)],
            ["\n\n", "", ""]
        ]
        t_vozac = Table(vozac_data, colWidths=[240, 140, 145])
        t_vozac.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#aaaaaa')),
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e9ecef')),
            ('PADDING', (0,0), (-1,-1), 6),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(t_vozac)
        story.append(Spacer(1, 15))

        story.append(Paragraph("- ispunjava skladistar na prijemu robe u skladistu", sec_hdr))
        story.append(Spacer(1, 4))
        
        skladiste_data = [
            [Paragraph("Robu preuzeo i kontrolirao (ime i prezime):", val_style), Paragraph("Datum:", val_style), Paragraph("Potpis:", val_style)],
            ["\n\n", "", ""]
        ]
        t_skladiste = Table(skladiste_data, colWidths=[240, 140, 145])
        t_skladiste.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#aaaaaa')),
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e9ecef')),
            ('PADDING', (0,0), (-1,-1), 6),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(t_skladiste)

        if idx < len(aktivni_nalozi) - 1:
            story.append(PageBreak())

    doc.build(story)
    buffer.seek(0)
    return buffer


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

    odabrani_dobavljac_opcija = c_dob1.selectbox("Odaberi postojeceg dobavljaca (ili unesi novog):", lista_dobavljaca, index=default_dob_index)

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
            
            default_tip_idx = 1 if pp_data and pp_data.get("Tip") == "Povrat" else 0
            tip = c1.selectbox("Tip dokumenta", ["Prikup", "Povrat"], index=default_tip_idx)
            
            komercijalist = c2.text_input("Podnositelj zahtjeva (Komercijalist)", value=pp_data.get("Komercijalist", "") if pp_data else "")
            datum = c3.date_input("Datum prikupa", datetime.now())

            c4, c5 = st.columns(2)
            dobavljac = c4.text_input("Dobavljac / Tvrtka", value=zadati_naziv)
            kontakt = c5.text_input("Kontakt telefon / Osoba", value=zadati_kontakt)

            c6, c7 = st.columns(2)
            adresa_prikupa = c6.text_input("Adresa prikupljanja", value=zadana_adresa, placeholder="npr. Tina Ujevica 28, Dugo Selo")
            adresa_dostave = c7.text_input("Adresa dostave", value="Makromikro grupa d.o.o., Vukomericka ulica 6, 10410 Velika Gorica")

            opis = st.text_area("Vrsta robe / Opis i kolicina", value=pp_data.get("Opis robe", "") if pp_data else "")
            napomena = st.text_input("Napomena za vozaca", value=zadana_napomena)

            submit = st.form_submit_button("Spremi Nalog", type="primary", use_container_width=True)

            if submit:
                if not komercijalist or not dobavljac or not adresa_prikupa or not opis:
                    st.error("Podnositelj, Dobavljac, Adresa prikupljanja i Vrsta robe su obavezni!")
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
                        "Status": "Na cekanju",
                        "Vrijeme Obrade": "-"
                    }
                    spremi_novi_nalog(novi_nalog)
                    st.session_state.baza_naloga = ucitaj_naloge()
                    st.session_state.baza_dobavljaca = ucitaj_dobavljace()
                    st.session_state.ponovi_prikup_data = None
                    st.success(f"Nalog {id_naloga} uspjesno spremljen! Podaci o dobavljacu zapamceni za ubuduce.")

    if pp_data:
        if st.button("❌ Ponisti ponovljeni unos"):
            st.session_state.ponovi_prikup_data = None
            st.rerun()

with tab2:
    col_h1, col_h2 = st.columns([3, 1])
    col_h1.subheader("📋 Upravljanje transportnim nalozima")
    if col_h2.button("🔄 Osvjezi podatke", use_container_width=True):
        st.session_state.baza_naloga = ucitaj_naloge()
        st.session_state.baza_dobavljaca = ucitaj_dobavljace()
        st.rerun()

    if not st.session_state.baza_naloga:
        st.info("Trenutno nema unesenih naloga u bazi.")
    else:
        with st.container(border=True):
            st.markdown("##### 🔍 Pretraga i Filteri")
            f_kol1, f_kol2, f_kol3, f_kol4 = st.columns(4)

            search_query = f_kol1.text_input("Pojam pretrage:", placeholder="HP, toner, ID...")

            sve_datume = sorted(list(set([x["Datum Prikupa"] for x in st.session_state.baza_naloga])), reverse=True)
            odabrani_datum = f_kol2.selectbox("Datum:", ["Svi datumi"] + sve_datume)

            svi_komercijalisti = sorted(list(set([x["Komercijalist"] for x in st.session_state.baza_naloga])))
            odabrani_komercijalist = f_kol3.selectbox("Komercijalist:", ["Svi"] + svi_komercijalisti)

            svi_dobavljaci_lista = sorted(list(set([x["Dobavljac"] for x in st.session_state.baza_naloga])))
            odabrani_dobavljac_filter = f_kol4.selectbox("Dobavljac:", ["Svi"] + svi_dobavljaci_lista)

        filtrirani = st.session_state.baza_naloga

        if odabrani_datum != "Svi datumi":
            filtrirani = [x for x in filtrirani if x["Datum Prikupa"] == odabrani_datum]

        if odabrani_komercijalist != "Svi":
            filtrirani = [x for x in filtrirani if x["Komercijalist"] == odabrani_komercijalist]

        if odabrani_dobavljac_filter != "Svi":
            filtrirani = [x for x in filtrirani if x["Dobavljac"] == odabrani_dobavljac_filter]

        if search_query:
            sq = search_query.lower()
            filtrirani = [
                x for x in filtrirani if 
                sq in x["ID Naloga"].lower() or 
                sq in x["Dobavljac"].lower() or 
                sq in x["Opis robe"].lower() or 
                sq in x["Komercijalist"].lower() or
                sq in x["Adresa Prikupa"].lower()
            ]

        aktivni_u_filtru = [x for x in filtrirani if x["Status"] != "Storno"]
        storno_u_filtru = [x for x in filtrirani if x["Status"] == "Storno"]
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Ukupno u prikazu", len(filtrirani))
        m2.metric("Aktivni nalozi", len(aktivni_u_filtru))
        m3.metric("Stornirani", len(storno_u_filtru))

        st.divider()

        if st.session_state.user_role == "admin":
            col_act1, col_act2 = st.columns(2)
            za_print = [x for x in filtrirani if x["Status"] in ["Na cekanju", "Isprintano"]]

            if za_print:
                pdf_bytes = generiraj_pdf_makromikro(za_print).getvalue()
                col_act1.download_button(
                    label=f"📄 Preuzmi PDF Zbirni Zahtjev ({len(za_print)} naloga)",
                    data=pdf_bytes,
                    file_name=f"Zahtjev_za_transport_zbirni_{datetime.now().strftime('%Y-%m-%d')}.pdf",
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True
                )
                if col_act1.button("✏️ Oznaci ove naloge kao 'Isprintano'", use_container_width=True):
                    for item in za_print:
                        if item["Status"] == "Na cekanju":
                            azuriraj_status_naloga(item["ID Naloga"], "Isprintano")
                    st.session_state.baza_naloga = ucitaj_naloge()
                    st.rerun()
            else:
                col_act1.info("Nema aktivnih naloga spremnih za ispis u ovom filteru.")

            if col_act2.button("✅ Oznaci SVE prikazane aktivne naloge kao PRIKUPLJENO", use_container_width=True):
                sada_str = f"{datetime.now().strftime('%d.%m.%Y. %H:%M')} (Admin)"
                brojac = 0
                for item in filtrirani:
                    if item["Status"] in ["Na cekanju", "Isprintano"]:
                        azuriraj_status_naloga(item["ID Naloga"], "Prikupljeno", sada_str)
                        brojac += 1
                st.session_state.baza_naloga = ucitaj_naloge()
                st.success(f"Status promijenjen u 'Prikupljeno' za {brojac} naloga!")
                st.rerun()

            with st.expander("⚠️ Napredno / Ciscenje baze (Admin zona)"):
                c_brisi1, c_brisi2 = st.columns(2)
                if c_brisi1.button("🗑️ Obrisi SVE naloge"):
                    if st.checkbox("Potvrdi brisanje naloga", key="p_nalozi"):
                        obrisi_sve_naloge()
                        st.session_state.baza_naloga = ucitaj_naloge()
                        st.success("Nalozi obrisani!")
                        st.rerun()
                if c_brisi2.button("🗑️ Obrisi SVE dobavljace"):
                    if st.checkbox("Potvrdi brisanje dobavljaca", key="p_dob"):
                        obrisi_sve_dobavljace()
                        st.session_state.baza_dobavljaca = ucitaj_dobavljace()
                        st.success("Dobavljaci obrisani!")
                        st.rerun()
            st.divider()

        statusi_opcije = ["Na cekanju", "Isprintano", "Prikupljeno", "Storno"]

        for i, nalog in enumerate(filtrirani):
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([1.2, 1.8, 2.5, 1.5, 2.2])
                
                c1.markdown(f"**{nalog['ID Naloga']}**")
                c1.caption(f"Tip: {nalog['Tip']}")
                
                c2.markdown(f"👤 **{nalog['Komercijalist']}**")
                c2.caption(f"📅 {nalog['Datum Prikupa']}")
                
                c3.markdown(f"🏢 **{nalog['Dobavljac']}**")
                c3.markdown(f"📍 _{nalog['Adresa Prikupa']}_")
                c3.caption(f"📦 {nalog['Opis robe']}")
                
                st_cls = "ai-badge-cekanje" if nalog['Status'] == "Na cekanju" else (
                    "ai-badge-isprintano" if nalog['Status'] == "Isprintano" else (
                        "ai-badge-prikupljeno" if nalog['Status'] == "Prikupljeno" else "ai-badge-storno"
                    )
                )
                c4.markdown(f"<span class='{st_cls}'>{nalog['Status']}</span>", unsafe_allow_html=True)
                if nalog['Vrijeme Obrade'] != "-":
                    c4.caption(f"Obrada: {nalog['Vrijeme Obrade']}")

                with c5:
                    if st.session_state.user_role == "admin":
                        trenutni_index = statusi_opcije.index(nalog['Status']) if nalog['Status'] in statusi_opcije else 0

                        novi_status = st.selectbox(
                            "Promijeni status",
                            statusi_opcije,
                            index=trenutni_index,
                            key=f"status_{nalog['ID Naloga']}_{i}",
                            label_visibility="collapsed"
                        )

                        if novi_status != nalog['Status']:
                            vrijeme = f"{datetime.now().strftime('%d.%m.%Y. %H:%M')} (Admin)" if novi_status == "Prikupljeno" else "-"
                            azuriraj_status_naloga(nalog['ID Naloga'], novi_status, vrijeme)
                            st.session_state.baza_naloga = ucitaj_naloge()
                            st.rerun()
                    else:
                        st.caption("🔒 Samo pregled statusa")

                    sub_c1, sub_c2 = st.columns(2)
                    
                    single_pdf_bytes = generiraj_pdf_makromikro([nalog]).getvalue()
                    sub_c1.download_button(
                        label="📄 PDF",
                        data=single_pdf_bytes,
                        file_name=f"Nalog_{nalog['ID Naloga']}.pdf",
                        mime="application/pdf",
                        key=f"pdf_single_{nalog['ID Naloga']}_{i}",
                        use_container_width=True
                    )

                    if sub_c2.button("🔄 Ponovi", key=f"ponovi_{nalog['ID Naloga']}_{i}", use_container_width=True):
                        st.session_state.ponovi_prikup_data = nalog
                        st.success("Kopirano! Prebacite se na karticu 'Unos'.")
