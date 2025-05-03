from datetime import datetime
import xlsxwriter
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from flask import make_response
import os
from cryptography.fernet import Fernet
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit



def generate_receipt(appointments, payments, person):
    total = 0
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 16)
    person_name = person.nome if person else "Sconosciuto"
    text = f"Quietanza di Pagamento per {person_name}"
    text_width = c.stringWidth(text, "Helvetica-Bold", 16)
    c.drawString((width - text_width) / 2, height - 40, text)
    c.line(30, height - 50, width - 30, height - 50)
    c.setFont("Helvetica", 12)
    y = height - 80
    for appointment in appointments:
        c.drawString(30, y, f"Cliente: {appointment.nome_cliente}")
        c.drawString(200, y, f"Data Appuntamento: {appointment.data_appuntamento.strftime('%Y-%m-%d')}")
        c.drawString(480, y, f"Pagamento: €{payments.get(str(appointment.id), 'N/A')}")
        total += float(payments.get(str(appointment.id), 0))
        y -= 20
        if y < 100:
            c.showPage()
            y = height - 80
            c.setFont("Helvetica", 12)
    c.line(30, y, width - 30, y)
    c.drawString(30, y - 20, f"Acconto: €{payments.get('acconto', 'N/A')}")
    c.drawString(30, y - 40, f"Saldo: €{total - payments.get('acconto', 0)}")
    
    if person:
        c.drawString(30, y - 60, f"Esenzione INPS maturata nell'anno in corso: €{person.totalYearlyPay * 1.22}")
    
    c.drawString(30, y - 80, f"Data: {datetime.now().strftime('%Y-%m-%d')}")
    c.drawString(30, y - 100, f"Firma: _______________________")
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue()


def changelogo(logo):
    print(logo)
    basedir = os.path.abspath(os.path.dirname(__file__))
    logo_path = os.path.join(basedir, 'static', 'logo.png')
    with open(logo_path, "wb") as file:
        file.write(logo)
        
def decrypt(key):
    with open("data_encrypted", "rb") as file:
        data = file.read()
    cipher_suite = Fernet(key)
    return cipher_suite.decrypt(data).decode()

from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit

def genera_fattura(appointments, payments, person):
    from app import Consultant
    provvigioni = (sum(float(payments.get(str(app.id), 0)) for app in appointments) + float(payments.get('extra', 0)))*1.21862667
    acconto = float(payments.get('acconto', 0))
    ritenuta_imposta = (provvigioni * 0.78)*0.23  # 23% sul 78%
    ritenuta_inps = 0.0  # Se necessario calcolare dinamicamente
    saldo = provvigioni - ritenuta_imposta - ritenuta_inps - acconto
    
    esenzione_inps = person.totalYearlyPay * 1.22 if person else 0.0
    
    now = datetime.now()
    fattura = {
        "data": now.strftime("%d/%m/%Y"),
        "provvigioni": provvigioni,
        "ritenuta_imposta": ritenuta_imposta,
        "ritenuta_inps": ritenuta_inps,
        "acconto": acconto,
        "saldo": saldo,
        "esclusione_inps": esenzione_inps
    }
    
    dati_cliente = {
        "nome": person.nome if person else "Cliente Sconosciuto",
        "cod_fiscale": person.CF if person else "",
        "telefono": person.phone if person else "",
        "email": person.email if person else "",
        "residenza": person.residency if person else ""
    }
    
    dati_azienda = {
        "nome": "PRESIDENT CUP S.R.L.",
        "indirizzo": "Via Tiburtina Valeria Km.112,500",
        "città": "67068 Scurcola Marsicana (AQ)",
        "partita_iva": "13629791008"
    }
    
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    def draw_text(c, x, y, text, size=10, bold=False):
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        for line in simpleSplit(text, c._fontname, size, width - x - 40):
            c.drawString(x, y, line)
            y -= size + 2
        return y
    
    y = height - 60
    draw_text(c, 40, y, f"{dati_cliente['nome']}", 12, True)
    draw_text(c, 40, y - 15, f"Cod. Fiscale: {dati_cliente['cod_fiscale']}")
    draw_text(c, 40, y - 30, f"Telefono: {dati_cliente['telefono']}")
    draw_text(c, 40, y - 45, f"Email: {dati_cliente['email']}")
    draw_text(c, 40, y - 60, f"Residenza: {dati_cliente['residenza']}")
    draw_text(c, width - 250, y, f"{dati_azienda['nome']}", 12, True)
    draw_text(c, width - 250, y - 15, f"{dati_azienda['indirizzo']}")
    draw_text(c, width - 250, y - 30, f"{dati_azienda['città']}")
    draw_text(c, width - 250, y - 45, f"P.IVA: {dati_azienda['partita_iva']}")
    
    y -= 90
    draw_text(c, 40, y, "QUIETANZA", 14, True)
    draw_text(c, 40, y - 20, f"Data emissione: {fattura['data']}")
    
    
    def monthintext():
        #when called, checks the current month, gets the prior month and return month and year
        now = datetime.now()
        month = now.month - 1 if now.month > 1 else 12
        year = now.year if now.month > 1 else now.year - 1
        months = ['Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno', 'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre']
        month_name = months[month - 1]  # Adjust for zero-based index
        return f"{month_name} {year}"
    
    
    y -= 40
    draw_text(c, 40, y, f"Provvigioni relative al mese di {monthintext()} per vendite a domicilio")
    draw_text(c, 40, y - 20, f"Provvigioni Occasionali: € {fattura['provvigioni']:.2f}")
    draw_text(c, 40, y - 40, f"Totale: € {fattura['provvigioni']:.2f}", 12, True)
    
    y -= 70
    draw_text(c, 40, y, f"Ritenuta a titolo d'Imposta: € {fattura['ritenuta_imposta']:.2f}")
    draw_text(c, 40, y - 20, f"Ritenuta previdenziale INPS: € {fattura['ritenuta_inps']:.2f}")
    draw_text(c, 40, y - 40, f"Acconto: € {fattura['acconto']:.2f}")
    draw_text(c, 40, y - 60, f"Saldo: € {fattura['saldo']:.2f}", 12, True)
    
    y -= 80
    draw_text(c, 40, y, f"Esclusione INPS maturata: € {fattura['esclusione_inps']:.2f}")
    
    y -= 100
    draw_text(c, 40, y, "Firma per ricevuta")
    c.line(40, y - 15, 200, y - 15)
    
    c.save()
    buffer.seek(0)
    return buffer.getvalue()
