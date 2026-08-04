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

# Pokušaj uvoz biblioteke za čitanje QR koda s fotografije
try:
    from PIL import Image as PilImage
    from pyzbar.pyzbar import decode as decode_qr
    PYZBAR_AVAILABLE = True
except ImportError:
    PYZBAR_AVAILABLE = False

st.set_page_config(page_title="Makromikro - AI Operations Hub", layout="wide", page_icon="📦")

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
                    "Vrijeme Obrade": r.get("vrijeme_obrade", "-")
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

def obrisi_sve_naloge():
    if supabase:
        try:
            supabase.table("nalozi").delete().neq("id", "NEPOSTOJECI_ID").execute()
        except Exception as e:
            st.error(f"Greska pri brisanju: {e}")

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

if "scanned_id" not in st.session_state:
    st.session_state.scanned_id = None

if "show_scanner_modal" not in st.session_state:
    st.session_state.show_scanner_modal = False

query_params = st.query_params
if len(query_params) > 0:
    st.session_state.is_logged_in = True
    st.session_state.user_role = query_params.get("role", "admin")
    if "search" in query_params:
        st.session_state.scanned_id = query_params.get("search")

# --- CSS STILOVI ---
st.markdown("""
    <style>
    .block-container { padding-top: 2rem; padding-bottom: 3rem; }
    .ai-badge-cekanje { background: rgba(245, 158, 11, 0.1); color: #d97706; border: 1px solid rgba(245, 158, 11, 0.2); padding: 4px 10px; border-radius: 20px; font-weight: 600; font-size: 0.75rem; }
    .ai-badge-isprintano { background: rgba(14, 165, 233, 0.1); color: #0284c7; border: 1px solid rgba(14, 165, 233, 0.2); padding: 4px 10px; border-radius: 20px; font-weight: 600; font-size: 0.75rem; }
    .ai-badge-prikupljeno { background: rgba(34, 197, 94, 0.1); color: #16a34a; border: 1px solid rgba(34, 197, 94, 0.2); padding: 4px 10px; border-radius: 20px; font-weight: 600; font-size: 0.75rem; }
    .ai-badge-storno { background: rgba(239, 68, 68, 0.1); color: #dc2626; border: 1px solid rgba(239, 68, 68, 0.2); padding: 4px 10px; border-radius: 20px; font-weight: 600; font-size: 0.75rem; text-decoration: line-through; }
    .ai-header-box { display: flex; align-items: center; justify-content: space-between; background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); padding: 16px 24px; border-radius: 12px; color: white; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

# --- PRIJAVA ---
if not st.session_state.is_logged_in:
    c_l1, c_l2, c_l3 = st.columns([1, 1.2, 1])
    with c_l2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("### ✨ Makromikro AI Hub")
            st.caption("Pristup transportnim nalozima i WMS logistici")
            
            if st.button("🚀 Brzi ulaz (Skladište / Vozač / Pregled)", type="primary", use_container_width=True):
                st.session_state.is_logged_in = True
                st.session_state.user_role = "admin"
                st.rerun()

            st.divider()
            unesena_lozinka = st.text_input("Ili unesite lozinku:", type="password")
            if st.button("Prijava", use_container_width=True):
                 if unesena_lozinka in ["admin123", ""]:
                     st.session_state.is_logged_in = True
                     st.session_state.user_role = "admin"
                     st.rerun()
                 else:
                     st.error("Pogrešna lozinka!")
    st.stop()

# --- GLAVNI IZLAZ ---
role_display = st.session_state.user_role.upper() if st.session_state.user_role else "ADMIN"
st.markdown(f"""
    <div class="ai-header-box">
        <div>
            <h2 style="margin:0; font-size: 1.4rem; font-weight: 700; color: #ffffff;">⚡ Makromikro Operations Hub</h2>
            <p style="margin:0; font-size: 0.85rem; color: #94a3b8;">Upravljanje prikupima i WMS logistikom</p>
        </div>
        <div style="background: rgba(255,255,255,0.1); padding: 6px 14px; border-radius: 20px; font-size: 0.85rem; font-weight: 600; color: #38bdf8;">
            Uloga: {role_display}
        </div>
    </div>
""", unsafe_allow_html=True)

col_top_btn1, col_top_btn2 = st.columns([5, 1.4])
with col_top_btn2:
    sub_c_cam, sub_c_out = st.columns(2)
    with sub_c_cam:
        if st.button("📷", help="Slikaj QR kod", use_container_width=True):
            st.session_state.show_scanner_modal = not st.session_state.show_scanner_modal
            st.rerun()
    with sub_c_out:
        if st.button("🔒", help="Odjava", use_container_width=True):
            st.session_state.is_logged_in = False
            st.session_state.user_role = None
            st.rerun()

if st.session_state.show_scanner_modal:
    with st.container(border=True):
        st.markdown("##### 📷 Slikanje QR koda kamerom")
        slika_qr = st.camera_input("Usmjerite kameru na kod")
        if slika_qr is not None and PYZBAR_AVAILABLE:
            try:
                img = PilImage.open(slika_qr)
                decoded_objects = decode_qr(img)
                if decoded_objects:
                    url_tekst = decoded_objects[0].data.decode('utf-8')
                    if "search=" in url_tekst:
                        s_id = url_tekst.split("search=")[1].split("&")[0]
                        st.session_state.scanned_id = s_id
                        st.query_params["search"] = s_id
                        st.session_state.show_scanner_modal = False
                        st.rerun()
            except Exception:
                pass
        if st.button("❌ Zatvori skener", use_container_width=True):
            st.session_state.show_scanner_modal = False
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
            qr_buf = generiraj_qr_sliku(f"{APP_URL}/?search={n['ID Naloga']}&role=admin")
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
    col_h1.subheader("📋 Pregled naloga")
    if col_h2.button("🔄 Osvježi", use_container_width=True):
        st.session_state.baza_naloga = ucitaj_naloge()
        st.session_state.baza_dobavljaca = ucitaj_dobavljace()
        st.rerun()

    if not st.session_state.baza_naloga:
        st.info("Nema unesenih naloga u bazi.")
    else:
        with st.container(border=True):
            search_query = st.text_input("🔍 Pretraga po ID-ju, dobavljaču ili opisu:", value=st.session_state.scanned_id or "")

        filtrirani = st.session_state.baza_naloga
        if search_query:
            sq = search_query.lower()
            filtrirani = [x for x in filtrirani if sq in x["ID Naloga"].lower() or sq in x["Dobavljac"].lower() or sq in x["Opis robe"].lower()]

        za_print = [x for x in filtrirani if x["Status"] in ["Na čekanju", "Isprintano"]]
        if za_print:
            pdf_bytes = generiraj_pdf_makromikro(za_print).getvalue()
            st.download_button(
                label=f"📄 Preuzmi PDF Zbirni Zahtjev ({len(za_print)} naloga)",
                data=pdf_bytes,
                file_name=f"Zahtjev_za_transport_{datetime.now().strftime('%Y-%m-%d')}.pdf",
                mime="application/pdf",
                type="primary"
            )

        st.divider()
        statusi_opcije = ["Na čekanju", "Isprintano", "Prikupljeno", "Storno"]

        for i, nalog in enumerate(filtrirani):
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([1.2, 1.8, 2.5, 1.5, 2.2])
                c1.markdown(f"**{nalog['ID Naloga']}**")
                c2.markdown(f"👤 **{nalog['Komercijalist']}**")
                c3.markdown(f"🏢 **{nalog['Dobavljac']}**<br>_{nalog['Adresa Prikupa']}_", unsafe_allow_html=True)
                c4.markdown(f"**{nalog['Status']}**")

                with c5:
                    novi_status = st.selectbox("Status", statusi_opcije, index=statusi_opcije.index(nalog['Status']) if nalog['Status'] in statusi_opcije else 0, key=f"st_{nalog['ID Naloga']}_{i}", label_visibility="collapsed")
                    if novi_status != nalog['Status']:
                        vrijeme = f"{datetime.now().strftime('%d.%m.%Y. %H:%M')}" if novi_status == "Prikupljeno" else "-"
                        azuriraj_status_naloga(nalog['ID Naloga'], novi_status, vrijeme)
                        st.session_state.baza_naloga = ucitaj_naloge()
                        st.rerun()

                    sub_c1, sub_c2 = st.columns(2)
                    single_pdf = generiraj_pdf_makromikro([nalog]).getvalue()
                    sub_c1.download_button("📄 PDF", single_pdf, file_name=f"Nalog_{nalog['ID Naloga']}.pdf", mime="application/pdf", key=f"p_{nalog['ID Naloga']}_{i}", use_container_width=True)
                    if sub_c2.button("🔄 Ponovi", key=f"r_{nalog['ID Naloga']}_{i}", use_container_width=True):
                        st.session_state.ponovi_prikup_data = nalog
                        st.rerun()
