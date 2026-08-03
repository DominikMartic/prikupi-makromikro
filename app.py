import streamlit as st
import pandas as pd
from datetime import datetime
import io

# ReportLab biblioteke za kreiranje čistog A4 PDF-a
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

st.set_page_config(page_title="Makromikro - Prikupi & Povrati", layout="wide", page_icon="📦")

# CSS Stilovi za moderan izgled
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { border-radius: 6px; font-weight: bold; }
    .status-cekanje { background-color: #ffeba2; color: #856404; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    .status-isprintano { background-color: #b8daff; color: #004085; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    .status-prikupljeno { background-color: #c3e6cb; color: #155724; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# Inicijalizacija baze u memoriji
if "baza_naloga" not in st.session_state:
    st.session_state.baza_naloga = []

st.title("📦 MAKROMIKRO GRUPA — Upravljanje Prikupima i Povratima")

# FUNKCIJA ZA GENERIRANJE PDF DOKUMENTA
def generiraj_pdf(nalozi_list):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30
    )
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#003366'),
        spaceAfter=6
    )
    
    sub_style = ParagraphStyle(
        'DocSub',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#cc0000'),
        spaceAfter=15
    )

    body_bold = ParagraphStyle('BodyBold', parent=styles['Normal'], fontSize=10, fontName='Helvetica-Bold')
    body_normal = ParagraphStyle('BodyNormal', parent=styles['Normal'], fontSize=10)

    for idx, n in enumerate(nalozi_list):
        # Zaglavlje
        story.append(Paragraph("MAKROMIKRO GRUPA d.o.o.", title_style))
        story.append(Paragraph(f"NALOG ZA {n['Tip'].upper()} ROBE — {n['ID Naloga']}", sub_style))

        # Tablica s informacijama
        info_data = [
            [Paragraph(f"<b>Datum prikupa:</b> {n['Datum Prikupa']}", body_normal), Paragraph(f"<b>Komercijalist:</b> {n['Komercijalist']}", body_normal)],
            [Paragraph(f"<b>Dobavljač:</b> {n['Dobavljač']}", body_normal), Paragraph(f"<b>Adresa / Kontakt:</b> {n['Adresa i Kontakt']}", body_normal)],
            [Paragraph(f"<b>Napomena za vozača:</b> {n['Napomena'] or '-'}", body_normal), ""]
        ]

        t_info = Table(info_data, colWidths=[260, 260])
        t_info.setStyle(TableStyle([
            ('SPAN', (0, 2), (1, 2)),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f2f4f7')),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d0d7de'))
        ]))
        story.append(t_info)
        story.append(Spacer(1, 15))

        # Opis robe
        opis_text = n['Opis robe'].replace('\n', '<br/>')
        opis_data = [
            [Paragraph("<b>OPIS ROBE / STAVKE ZA PREUZIMANJE</b>", body_bold)],
            [Paragraph(opis_text, body_normal)]
        ]
        t_opis = Table(opis_data, colWidths=[520])
        t_opis.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e1e8ed')),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#b0bec5')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(t_opis)
        story.append(Spacer(1, 40))

        # Potpisi
        potpis_data = [
            ["____________________________________", "____________________________________"],
            ["Potpis vozača / skladišta", "Potpis i pečat dobavljača"]
        ]
        t_potpis = Table(potpis_data, colWidths=[260, 260])
        t_potpis.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 1), (-1, 1), 9),
            ('TEXTCOLOR', (0, 1), (-1, 1), colors.HexColor('#555555'))
        ]))
        story.append(t_potpis)

        # Svaki nalog ide na novu stranicu
        if idx < len(nalozi_list) - 1:
            story.append(PageBreak())

    doc.build(story)
    buffer.seek(0)
    return buffer


# --- SUČELJE S KARTICAMA ---
tab1, tab2 = st.tabs(["➕ Unos Novog Naloga", "📋 Pregled, Print & Upravljanje"])

# 1. UNOS NALOGA
with tab1:
    st.subheader("Unos novog naloga (Komercijalist)")
    with st.form("forma_unos", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        tip = c1.selectbox("Tip dokumenta", ["Prikup", "Povrat"])
        komercijalist = c2.text_input("Komercijalist (Ime)")
        datum = c3.date_input("Datum prikupa", datetime.now())

        c4, c5 = st.columns(2)
        dobavljac = c4.text_input("Dobavljač")
        adresa = c5.text_input("Adresa i kontakt")

        opis = st.text_area("Opis robe / Stavke (Količine, palete, paketi)")
        napomena = st.text_input("Napomena za vozača")

        submit = st.form_submit_button("Spremi Nalog", type="primary")

        if submit:
            if not komercijalist or not dobavljac or not opis:
                st.error("Ime komercijalista, Dobavljač i Opis robe su obavezni!")
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
                st.success(f"Nalog {id_naloga} je uspješno spremljen sa statusom 'Na čekanju'!")

# 2. PREGLED I UPRAVLJANJE
with tab2:
    st.subheader("Filtriranje i Upravljanje Nalozima")

    if not st.session_state.baza_naloga:
        st.info("Trenutno nema unesenih naloga u sustavu.")
    else:
        # FILTER PO DATUMU
        sve_datume = sorted(list(set([x["Datum Prikupa"] for x in st.session_state.baza_naloga])), reverse=True)
        col_f1, col_f2 = st.columns([1, 2])
        odabrani_datum = col_f1.selectbox("Filter po datumu prikupa:", ["Svi datumi"] + sve_datume)

        if odabrani_datum == "Svi datumi":
            filtrirani = st.session_state.baza_naloga
        else:
            filtrirani = [x for x in st.session_state.baza_naloga if x["Datum Prikupa"] == odabrani_datum]

        st.divider()

        # GRUPNE AKCIJE
        st.subheader("Grupne akcije za filtrirane naloge")
        col_act1, col_act2 = st.columns(2)

        # Nalazi za print (Bilo da su 'Na čekanju' ili već 'Isprintano')
        za_print = [x for x in filtrirani if x["Status"] in ["Na čekanju", "Isprintano"]]

        if za_print:
            # Generiranje čistog PDF stream-a bez on_click greške
            pdf_bytes = generiraj_pdf(za_print).getvalue()
            
            btn_download = col_act1.download_button(
                label=f"📄 Preuzmi PDF za print ({len(za_print)} naloga)",
                data=pdf_bytes,
                file_name=f"NALOZI_{datetime.now().strftime('%Y-%m-%d')}.pdf",
                mime="application/pdf",
                type="primary"
            )

            # Ako želiš jednim klikom naknadno staviti status "Isprintano"
            if col_act1.button("✏️ Označi ove naloge kao 'Isprintano'"):
                for item in za_print:
                    if item["Status"] == "Na čekanju":
                        item["Status"] = "Isprintano"
                st.rerun()
        else:
            col_act1.info("Nema aktivnih naloga za generiranje PDF-a.")

        # Gumb za označavanje svih na kraju dana
        if col_act2.button("✅ Označi SVE prikazane naloge kao PRIKUPLJENO"):
            sada_str = datetime.now().strftime("%d.%m.%Y. %H:%M")
            brojac = 0
            for item in filtrirani:
                if item["Status"] in ["Na čekanju", "Isprintano"]:
                    item["Status"] = "Prikupljeno"
                    item["Vrijeme Obrade"] = sada_str
                    brojac += 1
            st.success(f"Uspješno označen status 'Prikupljeno' za {brojac} naloga!")
            st.rerun()

        st.divider()

        # POJEDINAČNI PRIKAZ I POPRAVAK STATUSIMA
        st.subheader("Pojedinačne postavke naloga")
        
        for i, nalog in enumerate(filtrirani):
            with st.container():
                c1, c2, c3, c4, c5 = st.columns([1.5, 2, 3, 1.5, 2])
                c1.write(f"**{nalog['ID Naloga']}** ({nalog['Tip']})")
                c2.write(f"👤 {nalog['Komercijalist']}\n📅 {nalog['Datum Prikupa']}")
                c3.write(f"🏢 **{nalog['Dobavljač']}**\n📦 {nalog['Opis robe']}")
                
                # Značka statusa
                st_cls = "status-cekanje" if nalog['Status'] == "Na čekanju" else ("status-isprintano" if nalog['Status'] == "Isprintano" else "status-prikupljeno")
                c4.markdown(f"<span class='{st_cls}'>{nalog['Status']}</span>", unsafe_allow_html=True)

                # Pojedinačni drop-down za promjenu statusa
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
