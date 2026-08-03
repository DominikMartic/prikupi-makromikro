from flask import Flask, render_template_string, request, redirect, url_for
from datetime import datetime
import sqlite3

app = Flask(__name__)

# Inicijalizacija baze podataka
def init_db():
    conn = sqlite3.connect('prikupi.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS nalozi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            broj_naloga TEXT,
            tip TEXT,
            komercijalist TEXT,
            datum_prikupa TEXT,
            dobavljac TEXT,
            adresa_kontakt TEXT,
            opis_robe TEXT,
            status TEXT,
            napomena TEXT,
            datum_obrade TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="hr">
<head>
    <meta charset="UTF-8">
    <title>Makromikro - Prikup i Povrat Robe</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f4f6f9; color: #333; }
        .container { max-width: 1100px; margin: auto; background: white; padding: 25px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1, h2 { color: #003366; }
        .logo { font-size: 24px; font-weight: bold; color: #003366; border-bottom: 3px solid #cc0000; padding-bottom: 5px; margin-bottom: 20px; }
        .logo span { color: #cc0000; }
        .form-group { margin-bottom: 15px; }
        label { display: block; font-weight: bold; margin-bottom: 5px; }
        input, select, textarea { width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
        .grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px; }
        .btn { background: #003366; color: white; border: none; padding: 10px 20px; cursor: pointer; border-radius: 4px; font-weight: bold; font-size: 14px; }
        .btn:hover { background: #002244; }
        .btn-success { background: #28a745; }
        .btn-success:hover { background: #218838; }
        .btn-print { background: #dc3545; }
        .btn-print:hover { background: #c82333; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { border: 1px solid #ddd; padding: 10px; text-align: left; }
        th { background-color: #003366; color: white; }
        tr:nth-child(even) { background-color: #f9f9f9; }
        .badge { padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }
        .badge-cekanje { background: #ffc107; color: #000; }
        .badge-prikupljeno { background: #28a745; color: white; }
        .actions { margin-top: 20px; display: flex; gap: 10px; }
        
        /* Stilovi za print na A4 */
        @media print {
            body { background: white; margin: 0; padding: 0; }
            .no-print { display: none !important; }
            .print-page { page-break-after: always; padding: 20px; border: none; }
            .print-header { border-bottom: 2px solid #003366; padding-bottom: 10px; margin-bottom: 20px; }
            .print-table { width: 100%; margin-top: 15px; }
            .signatures { margin-top: 50px; display: flex; justify-content: space-between; }
        }
    </style>
</head>
<body>

<div class="container no-print">
    <div class="logo">MAKROMIKRO <span>GRUPA</span> - Prikupi & Povrati</div>

    <h2>1. Unos novog naloga (Komercijalist)</h2>
    <form action="/dodaj" method="POST">
        <div class="grid">
            <div class="form-group">
                <label>Tip dokumenta:</label>
                <select name="tip" required>
                    <option value="Prikup">Prikup robe</option>
                    <option value="Povrat">Povrat dobavljaču</option>
                </select>
            </div>
            <div class="form-group">
                <label>Komercijalist:</label>
                <input type="text" name="komercijalist" placeholder="Vaše ime" required>
            </div>
            <div class="form-group">
                <label>Datum prikupa:</label>
                <input type="date" name="datum_prikupa" value="{{ danas }}" required>
            </div>
        </div>
        <div class="grid">
            <div class="form-group">
                <label>Dobavljač:</label>
                <input type="text" name="dobavljac" placeholder="Naziv tvrtke" required>
            </div>
            <div class="form-group">
                <label>Adresa i kontakt:</label>
                <input type="text" name="adresa_kontakt" placeholder="Ulica, Grad, Telefon" required>
            </div>
            <div class="form-group">
                <label>Napomena za vozača:</label>
                <input type="text" name="napomena" placeholder="npr. Zvati prije dolaska">
            </div>
        </div>
        <div class="form-group">
            <label>Opis robe / Stavke za preuzimanje:</label>
            <textarea name="opis_robe" rows="3" placeholder="Popis artikala, količine, broj koli ili paleta..." required></textarea>
        </div>
        <button type="submit" class="btn">Spremi Nalog</button>
    </form>

    <hr style="margin: 30px 0;">

    <h2>2. Popis svih naloga</h2>
    <div class="actions">
        <a href="/print-danas" target="_blank" class="btn btn-print">🖨️ Isprintaj sve DANAŠNJE naloge</a>
        <form action="/oznaci-prikupljeno" method="POST" style="margin:0;">
            <button type="submit" class="btn btn-success">✅ Označi današnje naloge kao PRIKUPLJENO</button>
        </form>
    </div>

    <table>
        <thead>
            <tr>
                <th>ID</th>
                <th>Tip</th>
                <th>Komercijalist</th>
                <th>Datum prikupa</th>
                <th>Dobavljač</th>
                <th>Opis robe</th>
                <th>Status</th>
                <th>Vrijeme obrade</th>
            </tr>
        </thead>
        <tbody>
            {% for row in nalozi %}
            <tr>
                <td><b>{{ row[1] }}</b></td>
                <td>{{ row[2] }}</td>
                <td>{{ row[3] }}</td>
                <td>{{ row[4] }}</td>
                <td><b>{{ row[5] }}</b><br><small>{{ row[6] }}</small></td>
                <td>{{ row[7] }}</td>
                <td>
                    {% if row[8] == 'Na čekanju' %}
                        <span class="badge badge-cekanje">Na čekanju</span>
                    {% else %}
                        <span class="badge badge-prikupljeno">Prikupljeno</span>
                    {% endif %}
                </td>
                <td>{{ row[10] or '-' }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>

</body>
</html>
'''

PRINT_TEMPLATE = '''
<!DOCTYPE html>
<html lang="hr">
<head>
    <meta charset="UTF-8">
    <title>Print Današnjih Naloga</title>
    <style>
        body { font-family: Arial, sans-serif; font-size: 14px; line-height: 1.4; }
        .page { page-break-after: always; padding: 30px; border: 1px solid #ccc; margin-bottom: 20px; }
        @media print { .page { border: none; padding: 0; margin: 0; } }
        .header { border-bottom: 2px solid #003366; padding-bottom: 10px; margin-bottom: 20px; }
        .title { font-size: 20px; font-weight: bold; color: #003366; }
        .info-table, .items-table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        .info-table td { padding: 6px; }
        .items-table th, .items-table td { border: 1px solid #333; padding: 10px; text-align: left; }
        .items-table th { background: #f0f0f0; }
        .signatures { margin-top: 60px; display: flex; justify-content: space-between; }
        .sig-box { width: 40%; text-align: center; border-top: 1px solid #000; padding-top: 5px; }
    </style>
</head>
<body onload="window.print()">
    {% for row in nalozi %}
    <div class="page">
        <div class="header">
            <div class="title">MAKROMIKRO GRUPA d.o.o.</div>
            <div>NALOG ZA {{ row[2]|upper }} ROBE - <b>{{ row[1] }}</b></div>
        </div>

        <table class="info-table">
            <tr>
                <td><b>Datum prikupa:</b> {{ row[4] }}</td>
                <td><b>Komercijalist:</b> {{ row[3] }}</td>
            </tr>
            <tr>
                <td><b>Dobavljač:</b> {{ row[5] }}</td>
                <td><b>Adresa & Kontakt:</b> {{ row[6] }}</td>
            </tr>
            <tr>
                <td colspan="2"><b>Napomena za vozača:</b> {{ row[9] or 'Nema napomene' }}</td>
            </tr>
        </table>

        <br>
        <table class="items-table">
            <thead>
                <tr>
                    <th>OPIS ROBE / STAVKE ZA PREUZIMANJE</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td style="height: 150px; vertical-align: top;">{{ row[7] }}</td>
                </tr>
            </tbody>
        </table>

        <div class="signatures">
            <div class="sig-box">Potpis vozača / skladišta</div>
            <div class="sig-box">Potpis i pečat dobavljača</div>
        </div>
    </div>
    {% endfor %}
</body>
</html>
'''

@app.route('/')
def index():
    danas = datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect('prikupi.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM nalozi ORDER BY id DESC')
    nalozi = cursor.fetchall()
    conn.close()
    return render_template_string(HTML_TEMPLATE, nalozi=nalozi, danas=danas)

@app.route('/dodaj', methods=['POST'])
def dodaj():
    tip = request.form['tip']
    komercijalist = request.form['komercijalist']
    datum_prikupa = request.form['datum_prikupa']
    dobavljac = request.form['dobavljac']
    adresa_kontakt = request.form['adresa_kontakt']
    opis_robe = request.form['opis_robe']
    napomena = request.form['napomena']

    conn = sqlite3.connect('prikupi.db')
    cursor = conn.cursor()
    
    # Generiranje rednog broja naloga
    prefix = "PR" if tip == "Prikup" else "POV"
    cursor.execute('SELECT COUNT(*) FROM nalozi')
    count = cursor.fetchone()[0] + 1
    broj_naloga = f"{prefix}-2026-{count:03d}"

    cursor.execute('''
        INSERT INTO nalozi (broj_naloga, tip, komercijalist, datum_prikupa, dobavljac, adresa_kontakt, opis_robe, status, napomena)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'Na čekanju', ?)
    ''', (broj_naloga, tip, komercijalist, datum_prikupa, dobavljac, adresa_kontakt, opis_robe, napomena))
    
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/print-danas')
def print_danas():
    danas = datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect('prikupi.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM nalozi WHERE datum_prikupa = ? AND status = "Na čekanju"', (danas,))
    nalozi = cursor.fetchall()
    conn.close()
    return render_template_string(PRINT_TEMPLATE, nalozi=nalozi)

@app.route('/oznaci-prikupljeno', methods=['POST'])
def oznaci_prikupljeno():
    danas = datetime.now().strftime('%Y-%m-%d')
    sada = datetime.now().strftime('%d.%m.%Y. %H:%M')
    conn = sqlite3.connect('prikupi.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE nalozi SET status = "Prikupljeno", datum_obrade = ? WHERE datum_prikupa = ? AND status = "Na čekanju"', (sada, danas))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
