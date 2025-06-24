import os
import sys
import re
import json
import datetime
import subprocess
import tempfile
from pathlib import Path
import base64
from io import BytesIO
import glob

# Función para verificar e instalar dependencias
def verificar_instalar_dependencias():
    """Verifica e instala las dependencias necesarias si no están presentes."""
    dependencias = ["pymupdf", "reportlab", "pillow"]
    
    print("Verificando e instalando dependencias necesarias...")
    
    if os.name == "nt":
        pip_commands = [f"\"{sys.executable}\" -m pip", "pip", "pip3"]
    else:
        pip_commands = [f"\"{sys.executable}\" -m pip", "pip3", "pip"]
    
    pip_exe = None
    for cmd in pip_commands:
        try:
            subprocess.run(f"{cmd} --version", shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            pip_exe = cmd
            break
        except:
            continue
    
    if not pip_exe:
        print("No se pudo encontrar pip. Por favor instale pip manualmente y vuelva a intentar.")
        return None
    
    for dep in dependencias:
        try:
            if dep == "pymupdf":
                __import__("fitz")
            elif dep == "pillow":
                __import__("PIL")
            else:
                __import__(dep)
            print(f"✓ {dep} ya está instalado")
        except ImportError:
            print(f"Instalando {dep}...")
            try:
                subprocess.run(f"{pip_exe} install {dep}", shell=True, check=True)
                print(f"✓ {dep} instalado correctamente")
            except subprocess.CalledProcessError:
                print(f"Error instalando {dep}. Intente instalarlo manualmente con: pip install {dep}")
                if dep == "pymupdf":
                    print("Nota: pymupdf también puede ser instalado como 'pip install PyMuPDF'")
    return None

def extraer_datos_pdf(ruta_pdf):
    """Extrae datos específicos de un PDF de informe de Cynet."""
    import fitz  # PyMuPDF
    
    doc = fitz.open(ruta_pdf)
    nombre_archivo = os.path.basename(ruta_pdf)
    nombre_informe = nombre_archivo.replace("ExecutiveReport_", "").replace(".pdf", "").replace("---", " - ")
    
    datos = {
        "nombre_informe": nombre_informe,
        "resumen": {
            "nombre": "N/A",
            "rango_fechas": "N/A",
            "generado": "N/A"
        },
        "malicioso": {
            "alertas_activadas": "0",
            "alertas_manejadas": "0",
            "archivos_afectados": "0",
            "archivos_remediados": "0",
            "endpoints_afectados": "0"
        },
        "automatizacion": {
            "investigaciones_auto": "0",
            "acciones_respuesta": "0"
        },
        "inventario": {
            "active_endpoints": "0"
        },
        "alert_severity_counts": { 
            "critical": "0",
            "high": "0",
            "medium": "0",
            "low": "0"
        },
        "fonts": []
    }
    
    texto_completo_pagina = ""
    if len(doc) > 0:
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp_txt_file:
                subprocess.run(["pdftotext", "-layout", ruta_pdf, tmp_txt_file.name], check=True)
                with open(tmp_txt_file.name, "r", encoding="utf-8") as f:
                    texto_completo_pagina = f.read()
            os.unlink(tmp_txt_file.name)
        except Exception as e_pdftotext:
            print(f"Advertencia: pdftotext falló ({e_pdftotext}), usando extracción de texto PyMuPDF para {nombre_informe}.")
            # Fallback a la extracción de texto integrada de PyMuPDF si pdftotext falla
            texto_completo_pagina = ""
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                texto_completo_pagina += page.get_text("text") # Extracción básica de texto

    match_resumen = re.search(r"Group Name\s*(.*?)\s*Date Range\s*(.*?)\s*Generated\s*(.*?)(?:\s*\*|$)", texto_completo_pagina, re.DOTALL | re.IGNORECASE)
    match_sitio = re.search(r"Site Name\s*(.*?)\s*Date Range", texto_completo_pagina, re.IGNORECASE)
    
    if match_resumen:
        datos["resumen"]["nombre"] = match_resumen.group(1).strip()
        datos["resumen"]["rango_fechas"] = match_resumen.group(2).strip()
        datos["resumen"]["generado"] = match_resumen.group(3).strip()
    elif match_sitio:
        datos["resumen"]["nombre"] = match_sitio.group(1).strip()
        match_rango_fechas = re.search(r"Date Range\s*(.*?)\s*Generated", texto_completo_pagina, re.IGNORECASE)
        match_generado = re.search(r"Generated\s*(.*?)(?:\s*\*|$)", texto_completo_pagina, re.IGNORECASE)
        if match_rango_fechas:
            datos["resumen"]["rango_fechas"] = match_rango_fechas.group(1).strip()
        if match_generado:
            generado_text_capture = match_generado.group(1) # Access the first and only capturing group
            if generado_text_capture:
                datos["resumen"]["generado"] = generado_text_capture.strip() # Corrected group index

    patron_malicioso = r"Malicious Detections and Preventions\s*(\d+)\s*Critical and\s*high alerts\s*were triggered\s*(\d+)\s*Critical and\s*high alerts\s*were handled\s*(\d+)\s*Affected files\s*(\d+)\s*Remediated files\s*(\d+)\s*Affected\s*endpoints"
    match_malicioso = re.search(patron_malicioso, texto_completo_pagina, re.DOTALL | re.IGNORECASE)
    if match_malicioso:
        datos["malicioso"]["alertas_activadas"] = match_malicioso.group(1).strip()
        datos["malicioso"]["alertas_manejadas"] = match_malicioso.group(2).strip()
        datos["malicioso"]["archivos_afectados"] = match_malicioso.group(3).strip()
        datos["malicioso"]["archivos_remediados"] = match_malicioso.group(4).strip()
        datos["malicioso"]["endpoints_afectados"] = match_malicioso.group(5).strip()

    patron_automatizacion = r"Automation\s*(\d+)\s*Automatic investigations\s*(\d+)\s*Response actions"
    match_automatizacion = re.search(patron_automatizacion, texto_completo_pagina, re.DOTALL | re.IGNORECASE)
    if match_automatizacion:
        datos["automatizacion"]["investigaciones_auto"] = match_automatizacion.group(1).strip()
        datos["automatizacion"]["acciones_respuesta"] = match_automatizacion.group(2).strip()
        
    patron_inventario = r"Inventory\*\s*(\d+)\s*Active Endpoints"
    match_inventario = re.search(patron_inventario, texto_completo_pagina, re.DOTALL | re.IGNORECASE)
    if match_inventario:
        datos["inventario"]["active_endpoints"] = match_inventario.group(1).strip()

    # Extracción de Alert Count by Severity - Lógica V7.1 más robusta
    alert_severity_block_match = re.search(r"Alert Count by Severity\s*Severity\s*#?\s*Alerts?\s*([\s\S]*?)(?:Top Affected Assets|Common Remediation Actions|IT Hygiene|Email Security|SaaS & Cloud|\Z)", texto_completo_pagina, re.IGNORECASE)
    
    if alert_severity_block_match:
        block_text = alert_severity_block_match.group(1)
        lines = block_text.split("\n")
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped: 
                continue
            severity_match = re.match(r"^(Critical|High|Medium|Low)\s+(\d+)$", line_stripped, re.IGNORECASE)
            if severity_match:
                severity_name = severity_match.group(1).lower()
                severity_count = severity_match.group(2).strip()
                if severity_name in datos["alert_severity_counts"]:
                    datos["alert_severity_counts"][severity_name] = severity_count
    else:
        print(f"Advertencia: bloque 'Alert Count by Severity' no encontrado en {nombre_informe}. Intentando búsqueda más amplia.")
        # Fallback: Buscar palabras clave de severidad seguidas de números en cualquier parte del texto
        severities_to_find = ["Critical", "High", "Medium", "Low"]
        for severity_keyword in severities_to_find:
            pattern_fallback = re.escape(severity_keyword) + r"\s+.*?(\d+)"
            matches_fallback = re.findall(pattern_fallback, texto_completo_pagina, re.IGNORECASE)
            if matches_fallback:
                datos["alert_severity_counts"][severity_keyword.lower()] = matches_fallback[0].strip()

    fonts = set()
    for page_idx in range(len(doc)):
        page = doc.load_page(page_idx)
        for font_info in page.get_fonts():
            if len(font_info) >= 4:
                font_name_pdf = font_info[3]
                if isinstance(font_name_pdf, str):
                    fonts.add(font_name_pdf)
    datos["fonts"] = list(fonts)
    
    doc.close()
    return datos

def crear_iconos_embebidos():
    """Crea iconos embebidos para usar en el informe."""
    from PIL import Image, ImageDraw
    import io

    icons_data = {}
    icon_size = (100,100)
    transparent_bg = (255, 255, 255, 0)

    # Icono de escudo (Detecciones Maliciosas)
    shield_img = Image.new("RGBA", icon_size, transparent_bg)
    draw = ImageDraw.Draw(shield_img)
    draw.polygon([(50, 10), (20, 25), (20, 55), (50, 90), (80, 55), (80, 25)], fill=(255, 255, 255), outline=(0,0,0), width=3)
    draw.polygon([(50, 20), (30, 30), (30, 55), (50, 80), (70, 55), (70, 30)], fill=(255, 20, 147))
    shield_buffer = io.BytesIO()
    shield_img.save(shield_buffer, format="PNG")
    icons_data["shield"] = shield_buffer.getvalue()

    # Icono de engranaje (Automatización)
    gear_img = Image.new("RGBA", icon_size, transparent_bg)
    draw = ImageDraw.Draw(gear_img)
    draw.ellipse([(25, 25), (75, 75)], fill=(255, 255, 255), outline=(10,46,54), width=3)
    draw.ellipse([(35, 35), (65, 65)], fill=(0, 229, 176))
    for i in range(8):
        angle = i * 45
        if angle % 90 == 0: 
             draw.rectangle([(45,10),(55,25)] if angle == 0 else [(45,75),(55,90)] if angle == 180 else 
                            [(10,45),(25,55)] if angle == 270 else [(75,45),(90,55)], fill=(10,46,54))
        elif angle % 45 == 0: 
            if angle == 45: draw.rectangle([(68,22),(78,32)], fill=(10,46,54))
            if angle == 135: draw.rectangle([(22,22),(32,32)], fill=(10,46,54))
            if angle == 225: draw.rectangle([(22,68),(32,78)], fill=(10,46,54))
            if angle == 315: draw.rectangle([(68,68),(78,78)], fill=(10,46,54))
    gear_buffer = io.BytesIO()
    gear_img.save(gear_buffer, format="PNG")
    icons_data["gear"] = gear_buffer.getvalue()

    # Icono de inventario (tres cubos)
    inventory_img = Image.new("RGBA", icon_size, transparent_bg)
    draw = ImageDraw.Draw(inventory_img)
    cube_size = 30
    top_cube_x, top_cube_y = 35, 20
    bottom_left_x, bottom_left_y = 20, 50
    bottom_right_x, bottom_right_y = 50, 50
    draw.polygon([(top_cube_x, top_cube_y + cube_size//2), (top_cube_x + cube_size//2, top_cube_y), 
                  (top_cube_x + cube_size, top_cube_y + cube_size//2), (top_cube_x + cube_size//2, top_cube_y + cube_size)], 
                 fill=(255,127,80), outline=(0,0,0), width=2)
    draw.polygon([(bottom_left_x, bottom_left_y + cube_size//2), (bottom_left_x + cube_size//2, bottom_left_y), 
                  (bottom_left_x + cube_size, bottom_left_y + cube_size//2), (bottom_left_x + cube_size//2, bottom_left_y + cube_size)], 
                 fill=(220,220,220), outline=(0,0,0), width=2)
    draw.polygon([(bottom_right_x, bottom_right_y + cube_size//2), (bottom_right_x + cube_size//2, bottom_right_y), 
                  (bottom_right_x + cube_size, bottom_right_y + cube_size//2), (bottom_right_x + cube_size//2, bottom_right_y + cube_size)], 
                 fill=(220,220,220), outline=(0,0,0), width=2)
    inventory_buffer = io.BytesIO()
    inventory_img.save(inventory_buffer, format="PNG")
    icons_data["inventory"] = inventory_buffer.getvalue()

    # Icono de Severidad de Alertas (gráfico de barras)
    alert_severity_img = Image.new("RGBA", icon_size, transparent_bg)
    draw = ImageDraw.Draw(alert_severity_img)
    bar_width = 15
    bar_spacing = 5
    max_bar_height = 70
    draw.rectangle([(15, 90 - max_bar_height*0.8), (15+bar_width, 90)], fill=(255,0,0), outline=(0,0,0))
    draw.rectangle([(15+bar_width+bar_spacing, 90 - max_bar_height*0.6), (15+2*bar_width+bar_spacing, 90)], fill=(255,165,0), outline=(0,0,0))
    draw.rectangle([(15+2*bar_width+2*bar_spacing, 90 - max_bar_height*0.4), (15+3*bar_width+2*bar_spacing, 90)], fill=(255,255,0), outline=(0,0,0))
    draw.rectangle([(15+3*bar_width+3*bar_spacing, 90 - max_bar_height*0.2), (15+4*bar_width+3*bar_spacing, 90)], fill=(0,128,0), outline=(0,0,0))
    alert_severity_buffer = io.BytesIO()
    alert_severity_img.save(alert_severity_buffer, format="PNG")
    icons_data["alert_severity"] = alert_severity_buffer.getvalue()

    return icons_data

def registrar_fuentes_cynet():
    """Registra fuentes personalizadas para el informe Cynet."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import os
    
    fonts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cynet_fonts")
    os.makedirs(fonts_dir, exist_ok=True)
    
    font_files = {
        "Segoe UI": {
            "normal": "segoeui.ttf", "bold": "segoeuib.ttf",
            "italic": "segoeuii.ttf", "bolditalic": "segoeuiz.ttf"
        },
        "Arial": {
            "normal": "arial.ttf", "bold": "arialbd.ttf",
            "italic": "ariali.ttf", "bolditalic": "arialbi.ttf"
        },
        "Roboto": {
            "normal": "Roboto-Regular.ttf", "bold": "Roboto-Bold.ttf",
            "italic": "Roboto-Italic.ttf", "bolditalic": "Roboto-BoldItalic.ttf"
        }
    }
    font_paths = []
    if os.name == "nt":
        font_paths.append(os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts"))
    else:
        font_paths.extend([
            "/usr/share/fonts", "/usr/local/share/fonts",
            os.path.expanduser("~/.fonts"), os.path.expanduser("~/Library/Fonts")
        ])
    
    registered_fonts = {}
    for font_name_key, variants in font_files.items():
        found_any_variant = False
        for variant_name, file_name in variants.items():
            for font_path_dir in font_paths:
                full_path = os.path.join(font_path_dir, file_name)
                if os.path.exists(full_path):
                    try:
                        font_id = f"{font_name_key}-{variant_name}"
                        pdfmetrics.registerFont(TTFont(font_id, full_path))
                        registered_fonts[variant_name] = font_id
                        found_any_variant = True
                    except Exception as e:
                        print(f"Error registrando fuente {font_id}: {e}")
            if found_any_variant and variant_name == "normal": 
                 if "bold" in variants and not "bold" in registered_fonts:
                     continue 
        if found_any_variant and "normal" in registered_fonts and "bold" in registered_fonts:
            break 
            
    if not ("normal" in registered_fonts and "bold" in registered_fonts):
        print("Usando fuentes predeterminadas de ReportLab ya que no se encontraron todas las fuentes personalizadas.")
        registered_fonts = {
            "normal": "Helvetica", "bold": "Helvetica-Bold",
            "italic": "Helvetica-Oblique", "bolditalic": "Helvetica-BoldOblique"
        }
    return registered_fonts

def crear_informe_unificado(datos_todos, ruta_salida, ruta_logo, iconos=None):
    """Crea un informe PDF unificado con estilo Cynet a partir de los datos extraídos."""
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib.units import inch
    from reportlab.graphics.shapes import Drawing, Rect
    from PIL import Image as PILImage
    import io

    cynet_blue = colors.Color(0/255, 102/255, 255/255)
    cynet_dark = colors.Color(51/255, 51/255, 51/255)
    cynet_light = colors.Color(240/255, 240/255, 240/255)

    fonts = registrar_fuentes_cynet()
    font_name = fonts.get("normal", "Helvetica")
    font_name_bold = fonts.get("bold", "Helvetica-Bold")

    doc = SimpleDocTemplate(ruta_salida, pagesize=landscape(letter),
                          leftMargin=0.5*inch, rightMargin=0.5*inch,
                          topMargin=0.75*inch, bottomMargin=0.75*inch)
    estilos = getSampleStyleSheet()
    estilo_titulo = ParagraphStyle("CynetTitle", parent=estilos["Heading1"], fontSize=22, fontName=font_name_bold, textColor=cynet_dark, alignment=0, spaceAfter=12)
    estilo_encabezado = ParagraphStyle("CynetHeading", parent=estilos["Heading2"], fontSize=16, fontName=font_name_bold, textColor=cynet_dark, alignment=0, spaceAfter=6)
    estilo_subencabezado = ParagraphStyle("CynetSubheading", parent=estilos["Heading3"], fontSize=14, fontName=font_name_bold, textColor=cynet_dark, spaceAfter=6)
    estilo_normal = ParagraphStyle("CynetNormal", parent=estilos["Normal"], fontSize=10, fontName=font_name, textColor=cynet_dark)

    contenido = []
    try:
        img = PILImage.open(ruta_logo)
        aspect_ratio = img.width / img.height
        logo_width = 1.5*inch
        logo_img = Image(ruta_logo, width=logo_width, height=logo_width / aspect_ratio)
    except Exception as e:
        print(f"Advertencia: No se pudo cargar el logo desde {ruta_logo}: {e}")
        d = Drawing(1.5*inch, 0.5*inch)
        d.add(Rect(0, 0, 1.5*inch, 0.5*inch, fillColor=cynet_blue))
        logo_img = d

    fecha_generacion = datetime.datetime.now().strftime("%d-%b-%Y")
    datos_encabezado_tabla = [[logo_img, Paragraph("Executive Summary", estilo_titulo)], ["", Paragraph(f"Unified Report - Generated: {fecha_generacion}", estilo_normal)]]
    tabla_encabezado = Table(datos_encabezado_tabla, colWidths=[2*inch, 8*inch])
    tabla_encabezado.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("ALIGN", (0,0), (0,-1), "LEFT"), ("ALIGN", (1,0), (1,-1), "LEFT"), ("BOTTOMPADDING", (0,0), (-1,-1), 12)]))
    contenido.append(tabla_encabezado)
    contenido.append(Spacer(1, 0.25*inch))

    datos_resumen_header = ["Report", "Critical/High Alerts", "Handled Alerts", "Affected Files", "Remediated Files", "Affected Endpoints", "Auto. Investigations", "Response Actions", "Active Endpoints"]
    datos_resumen = [datos_resumen_header]
    for datos_pdf in datos_todos:
        datos_resumen.append([
            datos_pdf["resumen"]["nombre"],
            datos_pdf["malicioso"]["alertas_activadas"],
            datos_pdf["malicioso"]["alertas_manejadas"],
            datos_pdf["malicioso"]["archivos_afectados"],
            datos_pdf["malicioso"]["archivos_remediados"],
            datos_pdf["malicioso"]["endpoints_afectados"],
            datos_pdf["automatizacion"]["investigaciones_auto"],
            datos_pdf["automatizacion"]["acciones_respuesta"],
            datos_pdf["inventario"]["active_endpoints"]
        ])

    totales = ["TOTAL"]
    for i in range(1, len(datos_resumen_header)):
        try:
            total_col = sum(int(fila[i]) for fila in datos_resumen[1:] if fila[i].isdigit())
            totales.append(str(total_col))
        except (ValueError, TypeError):
            totales.append("N/A") 
            
    datos_resumen.append(totales)
    page_width_actual = landscape(letter)[0] - 1*inch 
    num_cols_summary = len(datos_resumen_header)
    col_width_summary = page_width_actual / num_cols_summary
    col_widths_summary = [col_width_summary] * num_cols_summary
    col_widths_summary[0] = 2 * col_width_summary 
    remaining_width_summary = page_width_actual - col_widths_summary[0]
    other_col_width_summary = remaining_width_summary / (num_cols_summary -1)
    for i in range(1, num_cols_summary):
        col_widths_summary[i] = other_col_width_summary

    tabla_resumen = Table(datos_resumen, repeatRows=1, colWidths=col_widths_summary)
    tabla_resumen.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), cynet_blue), ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("BACKGROUND", (0,-1), (-1,-1), cynet_light), ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("FONTNAME", (0,0), (-1,0), font_name_bold), ("FONTNAME", (0,-1), (-1,-1), font_name_bold),
        ("BOTTOMPADDING", (0,0), (-1,0), 12), ("GRID", (0,0), (-1,-1), 1, colors.black),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("FONTSIZE", (0,0), (-1,-1), 7), ("WORDWRAP", (0,0), (-1,-1), True)
    ]))
    contenido.append(Paragraph("Comparative Summary", estilo_encabezado))
    contenido.append(Spacer(1, 0.1*inch))
    contenido.append(tabla_resumen)
    contenido.append(Spacer(1, 0.25*inch))

    icon_img_width = 0.4*inch
    icon_img_height = 0.4*inch
    shield_icon_img, gear_icon_img, inventory_icon_img, alert_severity_icon_img = "[ICON]", "[ICON]", "[ICON]", "[ICON]"
    if iconos:
        try:
            shield_icon_img = Image(BytesIO(iconos.get("shield")), width=icon_img_width, height=icon_img_height) if iconos.get("shield") else "[ICON]"
            gear_icon_img = Image(BytesIO(iconos.get("gear")), width=icon_img_width, height=icon_img_height) if iconos.get("gear") else "[ICON]"
            inventory_icon_img = Image(BytesIO(iconos.get("inventory")), width=icon_img_width, height=icon_img_height) if iconos.get("inventory") else "[ICON]"
            alert_severity_icon_img = Image(BytesIO(iconos.get("alert_severity")), width=icon_img_width, height=icon_img_height) if iconos.get("alert_severity") else "[ICON]"
        except Exception as e:
            print(f"Advertencia: No se pudieron cargar uno o más iconos desde los datos: {e}")

    for datos_pdf in datos_todos:
        nombre_informe_detalle = datos_pdf["resumen"]["nombre"]
        rango_fechas_detalle = datos_pdf["resumen"]["rango_fechas"]
        generado_detalle = datos_pdf["resumen"]["generado"]
        
        datos_titulo_informe_detalle = [[Paragraph(f"Report: {nombre_informe_detalle}", estilo_encabezado)]]
        tabla_titulo_informe_detalle = Table(datos_titulo_informe_detalle, colWidths=[page_width_actual])
        tabla_titulo_informe_detalle.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),cynet_light),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("ALIGN",(0,0),(-1,-1),"LEFT"),("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),10),("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)]))
        contenido.append(tabla_titulo_informe_detalle)
        contenido.append(Spacer(1, 0.1*inch))
        contenido.append(Paragraph(f"Date Range: {rango_fechas_detalle}", estilo_normal))
        contenido.append(Paragraph(f"Generated: {generado_detalle}", estilo_normal))
        contenido.append(Spacer(1, 0.1*inch))

        # Malicious Detections Section
        datos_titulo_malicioso_detalle = [[shield_icon_img, Paragraph("Malicious Detections and Preventions", estilo_subencabezado)]]
        tabla_titulo_malicioso_detalle = Table(datos_titulo_malicioso_detalle, colWidths=[0.5*inch, page_width_actual-0.5*inch])
        tabla_titulo_malicioso_detalle.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"MIDDLE"), ("ALIGN",(0,0),(0,-1),"CENTER"), ("ALIGN",(1,0),(1,-1),"LEFT"), ("LEFTPADDING",(0,0),(-1,-1),5), ("LINEABOVE",(0,0),(-1,0),2,cynet_blue)]))
        contenido.append(tabla_titulo_malicioso_detalle)
        contenido.append(Spacer(1, 0.1*inch))
        datos_maliciosos_detalle = [
            ["Metric", "Value"],
            ["Critical/high alerts triggered", datos_pdf["malicioso"]["alertas_activadas"]],
            ["Critical/high alerts handled", datos_pdf["malicioso"]["alertas_manejadas"]],
            ["Affected files", datos_pdf["malicioso"]["archivos_afectados"]],
            ["Remediated files", datos_pdf["malicioso"]["archivos_remediados"]],
            ["Affected endpoints", datos_pdf["malicioso"]["endpoints_afectados"]]
        ]
        tabla_maliciosos_detalle = Table(datos_maliciosos_detalle, colWidths=[4*inch, 1*inch])
        tabla_maliciosos_detalle.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),cynet_blue),("TEXTCOLOR",(0,0),(-1,0),colors.white),("ALIGN",(0,0),(-1,-1),"LEFT"),("ALIGN",(1,0),(1,-1),"CENTER"),("FONTNAME",(0,0),(-1,0),font_name_bold),("BOTTOMPADDING",(0,0),(-1,0),12),("GRID",(0,0),(-1,-1),1,colors.black),("VALIGN",(0,0),(-1,-1),"MIDDLE")]))
        contenido.append(tabla_maliciosos_detalle)
        contenido.append(Spacer(1, 0.2*inch))

        # Alert Count by Severity Section
        datos_titulo_alert_severity_detalle = [[alert_severity_icon_img, Paragraph("Alert Count by Severity", estilo_subencabezado)]]
        tabla_titulo_alert_severity_detalle = Table(datos_titulo_alert_severity_detalle, colWidths=[0.5*inch, page_width_actual-0.5*inch])
        tabla_titulo_alert_severity_detalle.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"MIDDLE"), ("ALIGN",(0,0),(0,-1),"CENTER"), ("ALIGN",(1,0),(1,-1),"LEFT"), ("LEFTPADDING",(0,0),(-1,-1),5), ("LINEABOVE",(0,0),(-1,0),2,cynet_blue)]))
        contenido.append(tabla_titulo_alert_severity_detalle)
        contenido.append(Spacer(1, 0.1*inch))
        datos_alert_severity_detalle = [
            ["Severity", "Count"],
            ["Critical", datos_pdf["alert_severity_counts"]["critical"]],
            ["High", datos_pdf["alert_severity_counts"]["high"]],
            ["Medium", datos_pdf["alert_severity_counts"]["medium"]],
            ["Low", datos_pdf["alert_severity_counts"]["low"]]
        ]
        tabla_alert_severity_detalle = Table(datos_alert_severity_detalle, colWidths=[4*inch, 1*inch])
        tabla_alert_severity_detalle.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),cynet_blue),("TEXTCOLOR",(0,0),(-1,0),colors.white),("ALIGN",(0,0),(-1,-1),"LEFT"),("ALIGN",(1,0),(1,-1),"CENTER"),("FONTNAME",(0,0),(-1,0),font_name_bold),("BOTTOMPADDING",(0,0),(-1,0),12),("GRID",(0,0),(-1,-1),1,colors.black),("VALIGN",(0,0),(-1,-1),"MIDDLE")]))
        contenido.append(tabla_alert_severity_detalle)
        contenido.append(Spacer(1, 0.2*inch))

        # Automation Section
        datos_titulo_auto_detalle = [[gear_icon_img, Paragraph("Automation", estilo_subencabezado)]]
        tabla_titulo_auto_detalle = Table(datos_titulo_auto_detalle, colWidths=[0.5*inch, page_width_actual-0.5*inch])
        tabla_titulo_auto_detalle.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"MIDDLE"), ("ALIGN",(0,0),(0,-1),"CENTER"), ("ALIGN",(1,0),(1,-1),"LEFT"), ("LEFTPADDING",(0,0),(-1,-1),5), ("LINEABOVE",(0,0),(-1,0),2,cynet_blue)]))
        contenido.append(tabla_titulo_auto_detalle)
        contenido.append(Spacer(1, 0.1*inch))
        datos_automatizacion_detalle = [
            ["Metric", "Value"],
            ["Automatic investigations", datos_pdf["automatizacion"]["investigaciones_auto"]],
            ["Response actions", datos_pdf["automatizacion"]["acciones_respuesta"]]
        ]
        tabla_automatizacion_detalle = Table(datos_automatizacion_detalle, colWidths=[4*inch, 1*inch])
        tabla_automatizacion_detalle.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),cynet_blue),("TEXTCOLOR",(0,0),(-1,0),colors.white),("ALIGN",(0,0),(-1,-1),"LEFT"),("ALIGN",(1,0),(1,-1),"CENTER"),("FONTNAME",(0,0),(-1,0),font_name_bold),("BOTTOMPADDING",(0,0),(-1,0),12),("GRID",(0,0),(-1,-1),1,colors.black),("VALIGN",(0,0),(-1,-1),"MIDDLE")]))
        contenido.append(tabla_automatizacion_detalle)
        contenido.append(Spacer(1, 0.2*inch))
        
        # Inventory Section
        datos_titulo_inventario_detalle = [[inventory_icon_img, Paragraph("Inventory", estilo_subencabezado)]]
        tabla_titulo_inventario_detalle = Table(datos_titulo_inventario_detalle, colWidths=[0.5*inch, page_width_actual-0.5*inch])
        tabla_titulo_inventario_detalle.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"MIDDLE"), ("ALIGN",(0,0),(0,-1),"CENTER"), ("ALIGN",(1,0),(1,-1),"LEFT"), ("LEFTPADDING",(0,0),(-1,-1),5), ("LINEABOVE",(0,0),(-1,0),2,cynet_blue)]))
        contenido.append(tabla_titulo_inventario_detalle)
        contenido.append(Spacer(1, 0.1*inch))
        datos_inventario_detalle = [
            ["Metric", "Value"],
            ["Active Endpoints", datos_pdf["inventario"]["active_endpoints"]]
        ]
        tabla_inventario_detalle = Table(datos_inventario_detalle, colWidths=[4*inch, 1*inch])
        tabla_inventario_detalle.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),cynet_blue),("TEXTCOLOR",(0,0),(-1,0),colors.white),("ALIGN",(0,0),(-1,-1),"LEFT"),("ALIGN",(1,0),(1,-1),"CENTER"),("FONTNAME",(0,0),(-1,0),font_name_bold),("BOTTOMPADDING",(0,0),(-1,0),12),("GRID",(0,0),(-1,-1),1,colors.black),("VALIGN",(0,0),(-1,-1),"MIDDLE")]))
        contenido.append(tabla_inventario_detalle)
        contenido.append(Spacer(1, 0.35*inch))

    def pie_pagina(canvas, doc_obj):
        canvas.saveState()
        canvas.setFont(font_name, 8)
        canvas.setFillColor(cynet_dark)
        footer_text = f"Unified Cynet Report - Generated: {fecha_generacion}"
        canvas.drawString(0.5*inch, 0.5*inch, footer_text)
        canvas.drawRightString(landscape(letter)[0] - 0.5*inch, 0.5*inch, f"Page {doc_obj.page}")
        canvas.restoreState()
    
    doc.build(contenido, onFirstPage=pie_pagina, onLaterPages=pie_pagina)
    return ruta_salida

def main():
    """Función principal que ejecuta el proceso completo."""
    print("=" * 80)
    print("  UNIFICADOR DE REPORTES CYNET PDF - v8.0 (Selección por Período)")
    print("=" * 80)
    print("\nEste script combina reportes PDF de Cynet en un único reporte unificado.")
    print("Extrae información específica y la presenta en un formato consolidado.\n")
    
    verificar_instalar_dependencias()
    
    import fitz  # PyMuPDF
    from datetime import datetime
    
    # Configurar codificación para consolas Windows
    if os.name == "nt":
        try:
            import codecs
            sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer)
        except:
            pass
    
    # Definir ruta predeterminada según el sistema operativo
    if os.name == "nt":  # Windows
        reports_dir = r"C:\Cynet_Reports"
    else:  # Linux/Mac
        home_dir = os.path.expanduser("~")
        reports_dir = os.path.join(home_dir, "Cynet_Reports")
    
    # Verificar si existe el directorio de reportes
    if not os.path.exists(reports_dir):
        print(f"Directorio predeterminado no encontrado: {reports_dir}")
        while True:
            respuesta = input("¿Crear este directorio (C), especificar otra ruta (E), o cancelar (X)? ").strip().upper()
            
            if respuesta == "C":
                try:
                    os.makedirs(reports_dir)
                    print(f"Directorio creado: {reports_dir}")
                    print(f"Por favor, coloque los archivos PDF de Cynet en: {reports_dir}")
                    print("\nPresione Enter para salir...")
                    input()
                    return
                except Exception as e:
                    print(f"Error al crear el directorio {reports_dir}: {e}")
            
            if respuesta == "E":
                nueva_ruta = input("Ingrese la ruta completa donde se encuentran los archivos PDF de Cynet: ").strip()
                
                # Eliminar comillas si el usuario las agregó
                if (nueva_ruta.startswith('"') and nueva_ruta.endswith('"')) or \
                   (nueva_ruta.startswith("'") and nueva_ruta.endswith("'")):
                    nueva_ruta = nueva_ruta[1:-1]
                
                if os.path.exists(nueva_ruta):
                    reports_dir = nueva_ruta
                    print(f"Usando directorio: {reports_dir}")
                    break
                else:
                    print(f"La ruta especificada no existe: {nueva_ruta}")
                    crear_dir = input("¿Crear este directorio? (S/N): ").strip().upper()
                    if crear_dir == "S":
                        try:
                            os.makedirs(nueva_ruta)
                            print(f"Directorio creado: {nueva_ruta}")
                            print(f"Por favor, coloque los archivos PDF de Cynet en: {nueva_ruta}")
                            print("\nPresione Enter para salir...")
                            input()
                            return
                        except Exception as e:
                            print(f"Error al crear el directorio {nueva_ruta}: {e}")
            
            elif respuesta == "X":
                print("Operación cancelada.")
                print("\nPresione Enter para salir...")
                input()
                return
            
            else:
                print("Opción no válida. Por favor, elija C, E o X.")
    
    # Buscar archivos PDF en el directorio
    pdf_files = glob.glob(os.path.join(reports_dir, "*.pdf"))
    
    if not pdf_files:
        print(f"No se encontraron archivos PDF en {reports_dir}")
        print(f"Por favor, coloque los archivos PDF de Cynet en: {reports_dir}")
        print("\nPresione Enter para salir...")
        input()
        return
    
    # Analizar los períodos disponibles en los archivos
    print("\nAnalizando archivos PDF encontrados...")
    
    # Patrón para extraer fechas del nombre del archivo
    # Ejemplo: ExecutiveReport_Demo-Console---AIO---SignUp---SaaS_8-Mar-2025---8-Apr-2025.pdf
    patron_fecha = r"(\d+-[A-Za-z]+-\d+)---(\d+-[A-Za-z]+-\d+)"
    
    # Lista para almacenar información de los períodos
    informes_disponibles = []
    
    # Diccionario para traducir nombres de meses
    meses_completos = {
        "Jan": "Enero", "Feb": "Febrero", "Mar": "Marzo", "Apr": "Abril",
        "May": "Mayo", "Jun": "Junio", "Jul": "Julio", "Aug": "Agosto",
        "Sep": "Septiembre", "Oct": "Octubre", "Nov": "Noviembre", "Dec": "Diciembre"
    }
    
    for archivo in pdf_files:
        nombre_archivo = os.path.basename(archivo)
        match = re.search(patron_fecha, nombre_archivo)
        
        if match:
            fecha_inicio = match.group(1)  # 8-Mar-2025
            fecha_fin = match.group(2)     # 8-Apr-2025
            
            # Extraer componentes de las fechas
            try:
                dia_inicio, mes_inicio_abr, año_inicio = fecha_inicio.split("-")
                dia_fin, mes_fin_abr, año_fin = fecha_fin.split("-")
                
                # Convertir a nombres completos de meses en español
                mes_inicio = meses_completos.get(mes_inicio_abr, mes_inicio_abr)
                mes_fin = meses_completos.get(mes_fin_abr, mes_fin_abr)
                
                # Crear descripción del período
                if mes_inicio == mes_fin and año_inicio == año_fin:
                    periodo = f"{mes_inicio} {año_inicio}"
                elif año_inicio == año_fin:
                    periodo = f"{mes_inicio} a {mes_fin} {año_inicio}"
                else:
                    periodo = f"{mes_inicio} {año_inicio} a {mes_fin} {año_fin}"
                
                # Almacenar información del informe
                informes_disponibles.append({
                    "archivo": archivo,
                    "periodo": periodo,
                    "fecha_inicio": fecha_inicio,
                    "fecha_fin": fecha_fin,
                    "nombre_archivo": nombre_archivo
                })
            except ValueError:
                # Si hay un error al procesar las fechas, omitir este archivo
                continue
    
    if not informes_disponibles:
        print("No se encontraron archivos con el formato de nombre esperado.")
        print("Los archivos deben tener un formato como: ExecutiveReport_Nombre_8-Mar-2025---8-Apr-2025.pdf")
        print("\nPresione Enter para salir...")
        input()
        return
    
    # Agrupar informes por período
    informes_por_periodo = {}
    for informe in informes_disponibles:
        periodo = informe["periodo"]
        if periodo not in informes_por_periodo:
            informes_por_periodo[periodo] = []
        informes_por_periodo[periodo].append(informe)
    
    # Mostrar períodos disponibles
    print("\nPeríodos disponibles en los reportes:")
    periodos = list(informes_por_periodo.keys())
    
    # Tratar de ordenar los períodos cronológicamente
    def get_sort_key(periodo):
        # Intentar extraer año y mes para ordenar
        if " a " in periodo:
            # Para períodos como "Marzo a Abril 2025"
            partes = periodo.split(" a ")
            if len(partes) == 2:
                inicio = partes[0]
                if " " in inicio:
                    mes, año = inicio.rsplit(" ", 1)
                    try:
                        año = int(año)
                        mes_idx = list(meses_completos.values()).index(mes) if mes in meses_completos.values() else 0
                        return año * 100 + mes_idx
                    except (ValueError, IndexError):
                        pass
        return periodo  # Si no podemos analizar, usar el texto completo
    
    periodos.sort(key=get_sort_key)
    
    for i, periodo in enumerate(periodos):
        cantidad = len(informes_por_periodo[periodo])
        print(f"  {i+1}. {periodo} ({cantidad} reportes)")
    
    # Solicitar al usuario el período que desea procesar
    while True:
        try:
            seleccion = input("\nSeleccione el número del período que desea procesar: ")
            indice = int(seleccion) - 1
            
            if 0 <= indice < len(periodos):
                periodo_seleccionado = periodos[indice]
                break
            else:
                print(f"Por favor, ingrese un número entre 1 y {len(periodos)}")
        except ValueError:
            print("Por favor, ingrese un número válido")
    
    # Obtener los archivos del período seleccionado
    informes_seleccionados = informes_por_periodo[periodo_seleccionado]
    rutas_pdf = [informe["archivo"] for informe in informes_seleccionados]
    
    print(f"\nSe procesarán {len(rutas_pdf)} archivos del período {periodo_seleccionado}:")
    for i, informe in enumerate(informes_seleccionados):
        print(f"  {i+1}. {informe['nombre_archivo']}")
    
    # Verificar si el logo de Cynet existe
    script_dir = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(script_dir, "cynet_logo.png")
    
    if not os.path.exists(logo_path):
        print("\nLogo de Cynet no encontrado, buscando en ubicaciones alternativas...")
        # Buscar en ubicaciones alternativas
        alt_locations = [
            os.path.join(os.path.dirname(script_dir), "cynet_logo.png"),
            os.path.join(os.path.dirname(script_dir), "cynet_style", "cynet_logo.png"),
            os.path.join(script_dir, "cynet_style", "cynet_logo.png"),
            os.path.join(script_dir, "cynet_icons", "cynet_logo_blue.png")
        ]
        
        for loc in alt_locations:
            if os.path.exists(loc):
                logo_path = loc
                print(f"Logo encontrado en: {logo_path}")
                break
        
        if not os.path.exists(logo_path):
            print("Advertencia: Logo de Cynet no encontrado. El reporte será generado sin logo.")
            # Usar un placeholder para el logo
            from PIL import Image, ImageDraw
            
            # Crear logo placeholder
            img = Image.new("RGB", (300, 100), color=(0, 102, 255))
            d = ImageDraw.Draw(img)
            d.text((20, 40), "CYNET", fill=(255, 255, 255))
            
            # Guardar logo placeholder
            os.makedirs(os.path.dirname(logo_path), exist_ok=True)
            img.save(logo_path)
            print(f"Logo temporal creado en: {logo_path}")
    
    # Crear iconos embebidos
    print("\nCreando iconos...")
    try:
        iconos = crear_iconos_embebidos()
        print("Iconos creados exitosamente.")
    except Exception as e:
        print(f"Advertencia: No se pudieron crear los iconos: {e}")
        iconos = None
    
    # Definir ruta de salida automáticamente con el período en el nombre
    # Reemplazar espacios y caracteres especiales para el nombre de archivo
    nombre_periodo = periodo_seleccionado.replace(" ", "_").replace("/", "-")
    ruta_salida = os.path.join(reports_dir, f"reporte_cynet_unificado_{nombre_periodo}.pdf")
    
    print("\nProcesando archivos PDF...")
    
    # Extraer datos de todos los PDFs
    todos_datos = []
    for ruta in rutas_pdf:
        print(f"Extrayendo datos de: {os.path.basename(ruta)}")
        datos = extraer_datos_pdf(ruta)
        todos_datos.append(datos)
        
        # Mostrar las fuentes encontradas (si están disponibles)
        if "fonts" in datos:
            print(f"Fuentes encontradas en {os.path.basename(ruta)}: {', '.join(datos['fonts'])}")
    
    # Crear informe unificado con estilo Cynet
    print("\nCreando reporte unificado con la marca Cynet...")
    ruta_final = crear_informe_unificado(todos_datos, ruta_salida, logo_path, iconos)
    
    print(f"\n✓ ¡Proceso completado exitosamente!")
    print(f"El reporte unificado de Cynet ha sido guardado en: {os.path.abspath(ruta_final)}")
    
    print("\nPresione Enter para salir...")
    input()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nError: {str(e)}")
        print("\nSe produjo un error inesperado. Por favor, intente nuevamente.")
        print("Si el problema persiste, contacte al equipo de Optimus.")
        print("\nPresione Enter para salir...")
        input()