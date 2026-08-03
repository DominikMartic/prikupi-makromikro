import streamlit as st
import pandas as pd
from datetime import datetime
import io
import html
import os

# ReportLab za profesionalni PDF izgled
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image

st.set_page_config(page_title="Makromikro - Prikupi & Povrati", layout="wide", page_icon="📦")

# CSS Stilovi za sučelje
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { border-radius: 6px; font-weight: bold; }
    .status-cekanje { background-color: #ffeba2; color: #856404; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    .status-isprintano { background-color: #b8daff; color: #004085; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    .status-prikupljeno { background-color: #c3e6cb; color: #155724; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

if "baza_naloga" not in st.session_state:
    st.session_state.baza_naloga = []

st.title("📦 MAKROMIKRO GRUPA — Upravljanje Prikupima i Povratima")

# Pomoćna funkcija za siguran unos teksta u PDF
def clean_txt(text):
    if not text:
        return "-"
    escaped = html.escape(str(text))
    return escaped.replace('\n', '<br/>')

# FUNKCIJA ZA DOKUMENT IDENTIČAN VAŠEM PDF OBRAZCU
def generiraj_pdf_makromikro(nalozi_list):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=35, leftMargin=35, topMargin=35, bottomMargin=35
    )
    story = []
    styles = getSampleStyleSheet()

    # Stilovi teksta
    header_title = ParagraphStyle('HeaderTitle', parent=styles['Normal'], fontSize=16, fontName='Helvetica-Bold', textColor=colors.HexColor('#003366'))
    header_sub = ParagraphStyle('HeaderSub', parent=styles['Normal'], fontSize=8, fontName='Helvetica', textColor=colors.HexColor('#333333'), leading=11)
    doc_title = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=15, fontName='Helvetica-Bold', alignment=1, spaceAfter=15, textColor=colors.HexColor('#003366'))
    
    lbl_style = ParagraphStyle('Lbl', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold', leading=12)
    val_style = ParagraphStyle('Val', parent=styles['Normal'], fontSize=9, fontName='Helvetica', leading=12)
    sec_hdr = ParagraphStyle('SecHdr', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold', textColor=colors.HexColor('#003366'))

    for idx, n in enumerate(nalozi_list):
        # 1. ZAGLAVLJE FIRME (Slika logo ako postoji, inače stilizirani tekst)
        if os.path.exists("logo.png"):
            logo_element = Image("logo.png", width=160, height=50)
            logo_element.hAlign = 'LEFT'
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

        # 2. NASLOV DOKUMENTA
        naslov_dokumenta = f"ZAHTJEV ZA TRANSPORT — {clean_txt(n['Tip']).upper()} ({clean_txt(n['ID Naloga'])})"
        story.append(Paragraph(naslov_dokumenta, doc_title))

        # 3. TABLICA S OSNOVNIM PODACIMA
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

        # 4. SEKCIJA VOZAČ
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

        # 5. SEKCIJA SKLADIŠTAR
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
    st.subheader("Unos novog naloga (Komercijalist)")
    with st.form("forma_unos", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        tip = c1.selectbox("Tip dokumenta", ["Prikup", "Povrat"])
        komercijalist = c2.text_input("Podnositelj zahtjeva (Komercijalist)")
        datum = c3.date_input("Datum prikupa", datetime.now())

        c4, c5 = st.columns(2)
        dobavljac = c4.text_input("Dobavljač / Tvrtka")
        kontakt = c5.text_input("Kontakt telefon / Osoba")

        c6, c7 = st.columns(2)
        adresa_prikupa = c6.text_input("Adresa prikupljanja", placeholder="npr. Tina Ujevića 28, Dugo Selo")
        adresa_dostave = c7.text_input("Adresa dostave", value="Makromikro grupa d.o.o., Vukomerička ulica 6, 10410 Velika Gorica")

        opis = st.text_area("Vrsta robe / Opis i količina (npr. Narudžba 9344 - vrećice za usisavač, 1 kom)")
        napomena = st.text_input("Napomena za vozača (npr. Nazvati 30 min prije dolaska)")

        submit = st.form_submit_button("Spremi Nalog", type="primary")

        if submit:
            if not komercijalist or not dobavljac or not adresa_prikupa or not opis:
                st.error("Podnositelj, Dobavljač, Adresa prikupljanja i Vrsta robe su obavezni!")
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
                    "Kontakt": kontakt or "-",
                    "Adresa Prikupa": adresa_prikupa,
                    "Adresa Dostave": adresa_dostave,
                    "Opis robe": opis,
                    "Napomena": napomena,
                    "Status": "Na čekanju",
                    "Vrijeme Obrade": "-"
                })
                st.success(f"Nalog {id_naloga} spremljen pod 'Na čekanju'!")

with tab2:
    st.subheader("Filtriranje i Upravljanje Nalozima")

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
                        item["Status"] = "Isprintano"
                st.rerun()
        else:
            col_act1.info("Nema naloga spremnih za ispis.")

        if col_act2.button("✅ Označi SVE prikazane naloge kao PRIKUPLJENO"):
            sada_str = datetime.now().strftime("%d.%m.%Y. %H:%M")
            brojac = 0
            for item in filtrirani:
                if item["Status"] in ["Na čekanju", "Isprintano"]:
                    item["Status"] = "Prikupljeno"
                    item["Vrijeme Obrade"] = sada_str
                    brojac += 1
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
                    nalog['Status'] = novi_status
                    if novi_status == "Prikupljeno":
                        nalog['Vrijeme Obrade'] = datetime.now().strftime("%d.%m.%Y. %H:%M")
                    st.rerun()

                st.markdown("<hr style='margin:8px 0; border:0.5px solid #eee;'>", unsafe_allow_html=True)
