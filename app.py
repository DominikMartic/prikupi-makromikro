import streamlit as st
import pandas as pd
from datetime import datetime
import io
import html
import os
from supabase import create_client, Client

# ReportLab za profesionalni PDF izgled
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image

st.set_page_config(page_title="Makromikro - Prikupi & Povrati", layout="wide", page_icon="📦")

# === PODACI ZA KONEKCIJU NA SUPABASE BAZU ===
SUPABASE_URL = "https://mxirprzgxtiwyhrmkyxv.supabase.co"
SUPABASE_KEY = "sb_publishable_2S7TjxGUgklILren3fJl0g_Gosq01mB"

@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    supabase = init_supabase()
except Exception:
    supabase = None

# --- SPREMANJE I UČITAVANJE IZ TRAJNE BAZE ---
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
                    "Dobavljač": r.get("dobavljac", "-"),
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
            # Vraća rječnik {naziv: {kontakt, adresa_prikupa, napomena}}
            return {d["naziv"]: d for d in data}
        except Exception:
            return {}
    return {}

def spremi_ili_azuriraj_dobavljaca(naziv, kontakt, adresa, napomena):
    if supabase and naziv and naziv != "Novi dobavljač...":
        try:
            podaci = {
                "naziv": naziv.strip(),
                "kontakt": kontakt.strip() if kontakt else "-",
                "adresa_prikupa": adresa.strip() if adresa else "-",
                "napomena": napomena.strip() if napomena else "-"
            }
            supabase.table("dobavljaci").upsert(podaci, on_conflict="naziv").execute()
        except Exception as e:
            st.error(f"Greška pri spremanju dobavljača: {e}")

def spremi_novi_nalog(n):
    if supabase:
        try:
            data = {
                "id": n["ID Naloga"],
                "tip": n["Tip"],
                "komercijalist": n["Komercijalist"],
                "datum_prikupa": n["Datum Prikupa"],
                "dobavljac": n["Dobavljač"],
                "kontakt": n["Kontakt"],
                "adresa_prikupa": n["Adresa Prikupa"],
                "adresa_dostave": n["Adresa Dostave"],
                "opis_robe": n["Opis robe"],
                "napomena": n["Napomena"],
                "status": n["Status"],
                "vrijeme_obrade": n["Vrijeme Obrade"]
            }
            supabase.table("nalozi").insert(data).execute()
            # Spremi/ažuriraj i u bazi dobavljača za buduće automatsko popunjavanje
            spremi_ili_azuriraj_dobavljaca(n["Dobavljač"], n["Kontakt"], n["Adresa Prikupa"], n["Napomena"])
        except Exception as e:
            st.error(f"Greška pri spremanju u bazu: {e}")

def azuriraj_status_naloga(id_naloga, novi_status, vrijeme_obrade="-"):
    if supabase:
        try:
            supabase.table("nalozi").update({
                "status": novi_status,
                "vrijeme_obrade": vrijeme_obrade
            }).eq("id", id_naloga).execute()
        except Exception as e:
            st.error(f"Greška pri ažuriranju: {e}")

# Inicijalizacija baze u session_state
if "baza_naloga" not in st.session_state:
    st.session_state.baza_naloga = ucitaj_naloge()

if "baza_dobavljaca" not in st.session_state:
    st.session_state.baza_dobavljaca = ucitaj_dobavljace()

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { border-radius: 6px; font-weight: bold; }
    .status-cekanje { background-color: #ffeba2; color: #856404; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    .status-isprintano { background-color: #b8daff; color: #004085; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    .status-prikupljeno { background-color: #c3e6cb; color: #155724; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.title("📦 MAKROMIKRO GRUPA — Upravljanje Prikupima i Povratima")

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

# FUNKCIJA ZA GENERIRANJE PDF-A
def generiraj_pdf_makromikro(nalozi_list):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=35, leftMargin=35, topMargin=35, bottomMargin=35
    )
    story = []
    styles = getSampleStyleSheet()

    header_title = ParagraphStyle('HeaderTitle', parent=styles['Normal'], fontSize=16, fontName='Helvetica-Bold', textColor=colors.HexColor('#003366'))
    header_sub = ParagraphStyle('HeaderSub', parent=styles['Normal'], fontSize=8, fontName='Helvetica', textColor=colors.HexColor('#333333'), leading=11)
    doc_title = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=15, fontName='Helvetica-Bold', alignment=1, spaceAfter=15, textColor=colors.HexColor('#003366'))
    
    lbl_style = ParagraphStyle('Lbl', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold', leading=12)
    val_style = ParagraphStyle('Val', parent=styles['Normal'], fontSize=9, fontName='Helvetica', leading=12)
    sec_hdr = ParagraphStyle('SecHdr', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold', textColor=colors.HexColor('#003366'))

    putanja_loga = nadji_logo()

    for idx, n in enumerate(nalozi_list):
        if putanja_loga:
            try:
                logo_element = Image(putanja_loga, width=150, height=45)
                logo_element.hAlign = 'LEFT'
            except Exception:
                logo_element = Paragraph("<b>makromikro</b><br/><font color='#cc0000'><b>GRUPA</b></font>", header_title)
        else:
            logo_element = Paragraph("<b>makromikro</b><br/><font color='#cc0000'><b>GRUPA</b></font>", header_title)

        info_text = Paragraph("<b>Makromikro grupa d.o.o.</b><br/>Vukomerička ulica 6,<br/>10410 Velika Gorica, Hrvatska<br/>OIB: 50467974870", header_sub)
        
        header_table = Table([[logo_element, info_text]], colWidths=[200, 325])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (1,0), (1,0), 'RIGHT')
        ]))
        story.append(header_table)
        story.append(Spacer(1, 15))

        naslov_dokumenta = f"ZAHTJEV ZA TRANSPORT — {clean_txt(n['Tip']).upper()} ({clean_txt(n['ID Naloga'])})"
        story.append(Paragraph(naslov_dokumenta, doc_title))

        podaci = [
            [Paragraph("Podnositelj zahtjeva:", lbl_style), Paragraph(clean_txt(n['Komercijalist']), val_style)],
            [Paragraph("Datum i vrijeme:", lbl_style), Paragraph(clean_txt(n['Datum Prikupa']), val_style)],
            [Paragraph("Dobavljač / Kontakt:", lbl_style), Paragraph(f"<b>{clean_txt(n['Dobavljač'])}</b> ({clean_txt(n['Kontakt'])})", val_style)],
            [Paragraph("Adresa prikupljanja:", lbl_style), Paragraph(clean_txt(n['Adresa Prikupa']), val_style)],
            [Paragraph("Adresa dostave (Mjesto otpreme):", lbl_style), Paragraph(clean_txt(n['Adresa Dostave']), val_style)],
            [Paragraph("Vrsta robe / Opis:", lbl_style), Paragraph(clean_txt(n['Opis robe']), val_style)],
            [Paragraph("Napomena za vozača:", lbl_style), Paragraph(clean_txt(n['Napomena']), val_style)],
        ]

        t_podaci = Table(podaci, colWidths=[160, 365])
        t_podaci.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
            ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f4f6f8')),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(t_podaci)
        story.append(Spacer(1, 15))

        story.append(Paragraph("- ispunjava vozač", sec_hdr))
        story.append(Spacer(1, 3))
        
        vozac_data = [
            [Paragraph("Prijevoz je izvršio (ime i prezime vozača):", val_style), Paragraph("Datum:", val_style), Paragraph("Potpis:", val_style)],
            ["\n", "", ""]
        ]
        t_vozac = Table(vozac_data, colWidths=[240, 140, 145])
        t_vozac.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#aaaaaa')),
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e9ecef')),
            ('PADDING', (0,0), (-1,-1), 5),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(t_vozac)
        story.append(Spacer(1, 15))

        story.append(Paragraph("- ispunjava skladištar na prijemu robe u skladištu", sec_hdr))
        story.append(Spacer(1, 3))
        
        skladiste_data = [
            [Paragraph("Robu preuzeo i kontrolirao (ime i prezime):", val_style), Paragraph("Datum:", val_style), Paragraph("Potpis:", val_style)],
            ["\n", "", ""]
        ]
        t_skladiste = Table(skladiste_data, colWidths=[240, 140, 145])
        t_skladiste.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#aaaaaa')),
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e9ecef')),
            ('PADDING', (0,0), (-1,-1), 5),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(t_skladiste)

        if idx < len(nalozi_list) - 1:
            story.append(PageBreak())

    doc.build(story)
    buffer.seek(0)
    return buffer


# --- SUČELJE APLIKACIJE ---
tab1, tab2 = st.tabs(["➕ Unos Novog Naloga", "📋 Pregled, Print & Upravljanje"])

with tab1:
    postojeci_logo = nadji_logo()
    if postojeci_logo:
        st.success(f"🖼️ Logo pronađen: `{postojeci_logo}`")
    else:
        st.warning("⚠️ Logo nije pronađen (`logo.png`).")

    st.subheader("Unos novog naloga (Komercijalist)")

    # Učitavanje spremnih dobavljača iz baze
    dobavljaci_dict = st.session_state.baza_dobavljaca
    lista_dobavljaca = ["Novi dobavljač..."] + sorted(list(dobavljaci_dict.keys()))

    c_dob1, c_dob2 = st.columns([1, 1])
    odabrani_dobavljac_opcija = c_dob1.selectbox("Odaberi postojećeg dobavljača (ili unesi novog):", lista_dobavljaca)

    if odabrani_dobavljac_opcija != "Novi dobavljač...":
        podaci_dob = dobavljaci_dict.get(odabrani_dobavljac_opcija, {})
        zadati_naziv = odabrani_dobavljac_opcija
        zadati_kontakt = podaci_dob.get("kontakt", "")
        zadana_adresa = podaci_dob.get("adresa_prikupa", "")
        zadana_napomena = podaci_dob.get("napomena", "")
        st.info(f"💡 Automatski povučeni podaci za dobavljača **{odabrani_dobavljac_opcija}**")
    else:
        zadati_naziv = ""
        zadati_kontakt = ""
        zadana_adresa = ""
        zadana_napomena = ""

    with st.form("forma_unos", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        tip = c1.selectbox("Tip dokumenta", ["Prikup", "Povrat"])
        komercijalist = c2.text_input("Podnositelj zahtjeva (Komercijalist)")
        datum = c3.date_input("Datum prikupa", datetime.now())

        c4, c5 = st.columns(2)
        dobavljac = c4.text_input("Dobavljač / Tvrtka", value=zadati_naziv)
        kontakt = c5.text_input("Kontakt telefon / Osoba", value=zadati_kontakt if zadati_kontakt != "-" else "")

        c6, c7 = st.columns(2)
        adresa_prikupa = c6.text_input("Adresa prikupljanja", value=zadana_adresa if zadana_adresa != "-" else "", placeholder="npr. Tina Ujevića 28, Dugo Selo")
        adresa_dostave = c7.text_input("Adresa dostave", value="Makromikro grupa d.o.o., Vukomerička ulica 6, 10410 Velika Gorica")

        opis = st.text_area("Vrsta robe / Opis i količina")
        napomena = st.text_input("Napomena za vozača", value=zadana_napomena if zadana_napomena != "-" else "")

        submit = st.form_submit_button("Spremi Nalog", type="primary")

        if submit:
            if not komercijalist or not dobavljac or not adresa_prikupa or not opis:
                st.error("Podnositelj, Dobavljač, Adresa prikupljanja i Vrsta robe su obavezni!")
            else:
                broj = len(st.session_state.baza_naloga) + 1
                prefiks = "PR" if tip == "Prikup" else "POV"
                id_naloga = f"{prefiks}-2026-{broj:03d}"
                
                novi_nalog = {
                    "ID Naloga": id_naloga,
                    "Tip": tip,
                    "Komercijalist": komercijalist,
                    "Datum Prikupa": datum.strftime("%Y-%m-%d"),
                    "Dobavljač": dobavljac,
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
                st.success(f"Nalog {id_naloga} uspješno spremljen! Podaci o dobavljaču zapamćeni za ubuduće.")

with tab2:
    st.subheader("Filtriranje i Upravljanje Nalozima")
    
    # Osvježi podatke iz baze na gumb
    if st.button("🔄 Osvježi podatke iz baze"):
        st.session_state.baza_naloga = ucitaj_naloge()
        st.session_state.baza_dobavljaca = ucitaj_dobavljace()
        st.rerun()

    if not st.session_state.baza_naloga:
        st.info("Trenutno nema unesenih naloga.")
    else:
        sve_datume = sorted(list(set([x["Datum Prikupa"] for x in st.session_state.baza_naloga])), reverse=True)
        col_f1, _ = st.columns([1, 2])
        odabrani_datum = col_f1.selectbox("Filter po datumu prikupa:", ["Svi datumi"] + sve_datume)

        filtrirani = st.session_state.baza_naloga if odabrani_datum == "Svi datumi" else [x for x in st.session_state.baza_naloga if x["Datum Prikupa"] == odabrani_datum]

        st.divider()
        col_act1, col_act2 = st.columns(2)

        za_print = [x for x in filtrirani if x["Status"] in ["Na čekanju", "Isprintano"]]

        if za_print:
            pdf_bytes = generiraj_pdf_makromikro(za_print).getvalue()
            col_act1.download_button(
                label=f"📄 Preuzmi PDF Zahtjev za Transport ({len(za_print)} naloga)",
                data=pdf_bytes,
                file_name=f"Zahtjev_za_transport_{datetime.now().strftime('%Y-%m-%d')}.pdf",
                mime="application/pdf",
                type="primary"
            )
            if col_act1.button("✏️ Označi ove naloge kao 'Isprintano'"):
                for item in za_print:
                    if item["Status"] == "Na čekanju":
                        azuriraj_status_naloga(item["ID Naloga"], "Isprintano")
                st.session_state.baza_naloga = ucitaj_naloge()
                st.rerun()
        else:
            col_act1.info("Nema naloga spremnih za ispis.")

        if col_act2.button("✅ Označi SVE prikazane naloge kao PRIKUPLJENO"):
            sada_str = datetime.now().strftime("%d.%m.%Y. %H:%M")
            brojac = 0
            for item in filtrirani:
                if item["Status"] in ["Na čekanju", "Isprintano"]:
                    azuriraj_status_naloga(item["ID Naloga"], "Prikupljeno", sada_str)
                    brojac += 1
            st.session_state.baza_naloga = ucitaj_naloge()
            st.success(f"Status promijenjen u 'Prikupljeno' za {brojac} naloga!")
            st.rerun()

        st.divider()
        st.subheader("Pojedinačne postavke naloga")

        for i, nalog in enumerate(filtrirani):
            with st.container():
                c1, c2, c3, c4, c5 = st.columns([1.5, 2, 3, 1.5, 2])
                c1.write(f"**{nalog['ID Naloga']}** ({nalog['Tip']})")
                c2.write(f"👤 {nalog['Komercijalist']}\n📅 {nalog['Datum Prikupa']}")
                c3.write(f"🏢 **{nalog['Dobavljač']}**\n📍 *Prikup:* {nalog['Adresa Prikupa']}\n📦 {nalog['Opis robe']}")
                
                st_cls = "status-cekanje" if nalog['Status'] == "Na čekanju" else ("status-isprintano" if nalog['Status'] == "Isprintano" else "status-prikupljeno")
                c4.markdown(f"<span class='{st_cls}'>{nalog['Status']}</span>", unsafe_allow_html=True)

                novi_status = c5.selectbox(
                    "Status",
                    ["Na čekanju", "Isprintano", "Prikupljeno"],
                    index=["Na čekanju", "Isprintano", "Prikupljeno"].index(nalog['Status']),
                    key=f"status_{nalog['ID Naloga']}_{i}"
                )

                if novi_status != nalog['Status']:
                    vrijeme = datetime.now().strftime("%d.%m.%Y. %H:%M") if novi_status == "Prikupljeno" else "-"
                    azuriraj_status_naloga(nalog['ID Naloga'], novi_status, vrijeme)
                    st.session_state.baza_naloga = ucitaj_naloge()
                    st.rerun()

                st.markdown("<hr style='margin:8px 0; border:0.5px solid #eee;'>", unsafe_allow_html=True)
