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

# Función para verificar e instalar dependencias
# Función para verificar e instalar dependencias
def verificar_instalar_dependencias():
    """Verifica e instala las dependencias necesarias si no están presentes."""
    dependencias = ['pymupdf', 'reportlab', 'pillow']
    
    # Usar pip directamente sin entorno virtual para simplificar
    print("Verificando e instalando dependencias...")
    
    # Determinar el comando pip a usar
    if os.name == 'nt':  # Windows
        pip_commands = ['pip', 'pip3', f'"{sys.executable}" -m pip']
    else:  # Unix/Linux/Mac
        pip_commands = ['pip3', 'pip', f'"{sys.executable}" -m pip']
    
    # Encontrar un comando pip que funcione
    pip_exe = None
    for cmd in pip_commands:
        try:
            subprocess.run(f'{cmd} --version', shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            pip_exe = cmd
            break
        except:
            continue
    
    if not pip_exe:
        print("No se pudo encontrar pip. Por favor instale pip manualmente y vuelva a intentar.")
        return None
    
    # Instalar dependencias
    for dep in dependencias:
        try:
            # Intentar importar la dependencia
            if dep == 'pymupdf':
                __import__('fitz')
            elif dep == 'pillow':
                __import__('PIL')
            else:
                __import__(dep)
            print(f"[OK] {dep} ya está instalado")
        except ImportError:
            print(f"Instalando {dep}...")
            try:
                subprocess.run(f'{pip_exe} install {dep}', shell=True, check=True)
                print(f"[OK] {dep} instalado correctamente")
            except subprocess.CalledProcessError:
                print(f"Error instalando {dep}. Intente instalarlo manualmente corriendo: pip install {dep}")
                if dep == 'pymupdf':
                    print("Nota: pymupdf también puede ser instalado corriendo 'pip install PyMuPDF'")
    
    return None

# Función para extraer datos de los PDFs
def extraer_datos_pdf(ruta_pdf):
    """Extrae datos específicos de un PDF de informe de Cynet."""
    import fitz  # PyMuPDF
    
    doc = fitz.open(ruta_pdf)
    
    # Obtener el nombre del archivo para usar como nombre del informe
    nombre_archivo = os.path.basename(ruta_pdf)
    nombre_informe = nombre_archivo.replace('ExecutiveReport_', '').replace('.pdf', '').replace('---', ' - ')
    
    datos = {
        'nombre_informe': nombre_informe,
        'resumen': {},
        'malicioso': {},
        'automatizacion': {}
    }
    
    # Extraer texto de la primera página donde está la mayoría de los datos objetivo
    texto_pagina = doc[0].get_text()
    
    # Extraer datos del Resumen Ejecutivo (primer recuadro rojo)
    match_resumen = re.search(r'Group Name\s*(.*?)\s*Date Range\s*(.*?)\s*Generated\s*(.*?)\s*\*', texto_pagina, re.DOTALL)
    match_sitio = re.search(r'Site Name\s*(.*?)\s*Date Range', texto_pagina)
    
    if match_resumen:
        datos['resumen']['nombre'] = match_resumen.group(1).strip()
        datos['resumen']['rango_fechas'] = match_resumen.group(2).strip()
        datos['resumen']['generado'] = match_resumen.group(3).strip()
    elif match_sitio:
        datos['resumen']['nombre'] = match_sitio.group(1).strip()
        match_rango_fechas = re.search(r'Date Range\s*(.*?)\s*Generated', texto_pagina)
        match_generado = re.search(r'Generated\s*(.*?)\s*\*', texto_pagina)
        
        if match_rango_fechas:
            datos['resumen']['rango_fechas'] = match_rango_fechas.group(1).strip()
        if match_generado:
            datos['resumen']['generado'] = match_generado.group(1).strip()
    
    # Extraer datos de Detecciones Maliciosas (segundo recuadro rojo)
    patron_malicioso = r'Malicious Detections and Preventions\s*(\d+)\s*Critical and\s*high alerts\s*were triggered\s*(\d+)\s*Critical and\s*high alerts\s*were handled\s*(\d+)\s*Affected files\s*(\d+)\s*Remediated files\s*(\d+)\s*Affected\s*endpoints'
    match_malicioso = re.search(patron_malicioso, texto_pagina, re.DOTALL)
    
    if match_malicioso:
        datos['malicioso']['alertas_activadas'] = match_malicioso.group(1).strip()
        datos['malicioso']['alertas_manejadas'] = match_malicioso.group(2).strip()
        datos['malicioso']['archivos_afectados'] = match_malicioso.group(3).strip()
        datos['malicioso']['archivos_remediados'] = match_malicioso.group(4).strip()
        datos['malicioso']['endpoints_afectados'] = match_malicioso.group(5).strip()
    
    # Extraer datos de Automatización (tercer recuadro rojo)
    patron_automatizacion = r'Automation\s*(\d+)\s*Automatic investigations\s*(\d+)\s*Response actions'
    match_automatizacion = re.search(patron_automatizacion, texto_pagina, re.DOTALL)
    
    if match_automatizacion:
        datos['automatizacion']['investigaciones_auto'] = match_automatizacion.group(1).strip()
        datos['automatizacion']['acciones_respuesta'] = match_automatizacion.group(2).strip()
    
    # Extraer información sobre fuentes utilizadas
    fonts = set()
    for page in doc:
        for font in page.get_fonts():
            if len(font) >= 4:  # Asegurarse de que hay suficientes elementos en la tupla
                font_name = font[3]
                if isinstance(font_name, str):
                    fonts.add(font_name)
    
    # Guardar las fuentes encontradas
    datos['fonts'] = list(fonts)
    
    doc.close()
    return datos

# Función para crear iconos embebidos
def crear_iconos_embebidos():
    """Crea iconos embebidos para usar en el informe."""
    from PIL import Image, ImageDraw
    import io
    
    # Crear icono de escudo (Malicious Detections)
    shield_img = Image.new('RGBA', (100, 100), color=(255, 255, 255, 0))
    draw = ImageDraw.Draw(shield_img)
    
    # Dibujar escudo
    draw.polygon([(50, 10), (20, 25), (20, 55), (50, 90), (80, 55), (80, 25)], 
                 fill=(255, 255, 255), outline=(0, 0, 0))
    draw.polygon([(50, 20), (30, 30), (30, 55), (50, 80), (70, 55), (70, 30)], 
                 fill=(255, 20, 147), outline=None)
    
    # Guardar en memoria
    shield_buffer = io.BytesIO()
    shield_img.save(shield_buffer, format="PNG")
    shield_data = shield_buffer.getvalue()
    
    # Crear icono de engranaje (Automation)
    gear_img = Image.new('RGBA', (100, 100), color=(255, 255, 255, 0))
    draw = ImageDraw.Draw(gear_img)
    
    # Dibujar círculo central
    draw.ellipse([(25, 25), (75, 75)], fill=(255, 255, 255), outline=(10, 46, 54))
    draw.ellipse([(35, 35), (65, 65)], fill=(0, 229, 176), outline=None)
    
    # Dibujar dientes del engranaje
    for i in range(8):
        angle = i * 45
        x1 = 50 + 40 * (angle % 90 == 0)
        y1 = 50 + 40 * (angle % 180 == 90)
        x2 = 50 - 40 * (angle % 90 == 0)
        y2 = 50 - 40 * (angle % 180 == 90)
        draw.rectangle([(x1-5, y1-5), (x1+5, y1+5)], fill=(10, 46, 54), outline=None)
        
    # Guardar en memoria
    gear_buffer = io.BytesIO()
    gear_img.save(gear_buffer, format="PNG")
    gear_data = gear_buffer.getvalue()
    
    return {
        'shield': shield_data,
        'gear': gear_data
    }

# Función para registrar fuentes personalizadas
def registrar_fuentes_cynet():
    """Registra fuentes personalizadas para el informe Cynet."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import os
    
    # Directorio para guardar las fuentes
    fonts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cynet_fonts")
    os.makedirs(fonts_dir, exist_ok=True)
    
    # Intentar registrar fuentes comunes que podrían parecerse a las de Cynet
    font_files = {
        'Segoe UI': {
            'normal': 'segoeui.ttf',
            'bold': 'segoeuib.ttf',
            'italic': 'segoeuii.ttf',
            'bolditalic': 'segoeuiz.ttf'
        },
        'Arial': {
            'normal': 'arial.ttf',
            'bold': 'arialbd.ttf',
            'italic': 'ariali.ttf',
            'bolditalic': 'arialbi.ttf'
        },
        'Roboto': {
            'normal': 'Roboto-Regular.ttf',
            'bold': 'Roboto-Bold.ttf',
            'italic': 'Roboto-Italic.ttf',
            'bolditalic': 'Roboto-BoldItalic.ttf'
        }
    }
    
    # Buscar en ubicaciones comunes de fuentes
    font_paths = []
    if os.name == 'nt':  # Windows
        font_paths.append(os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts'))
    else:  # Unix/Linux/Mac
        font_paths.extend([
            '/usr/share/fonts',
            '/usr/local/share/fonts',
            os.path.expanduser('~/.fonts'),
            os.path.expanduser('~/Library/Fonts')
        ])
    
    # Registrar fuentes
    registered_fonts = {}
    
    # Primero intentar con fuentes del sistema
    for font_name, variants in font_files.items():
        found = False
        for variant_name, file_name in variants.items():
            for font_path in font_paths:
                full_path = os.path.join(font_path, file_name)
                if os.path.exists(full_path):
                    try:
                        font_id = f"{font_name}-{variant_name}"
                        pdfmetrics.registerFont(TTFont(font_id, full_path))
                        registered_fonts[variant_name] = font_id
                        found = True
                        print(f"Registered font: {font_id} from {full_path}")
                    except Exception as e:
                        print(f"Error registering font {font_id}: {e}")
        
        if found:
            break
    
    # Si no se encontraron fuentes, usar las predeterminadas de ReportLab
    if not registered_fonts:
        registered_fonts = {
            'normal': 'Helvetica',
            'bold': 'Helvetica-Bold',
            'italic': 'Helvetica-Oblique',
            'bolditalic': 'Helvetica-BoldOblique'
        }
        print("Using default ReportLab fonts")
    
    return registered_fonts

# Función para crear el informe unificado con estilo Cynet
def crear_informe_unificado(datos_todos, ruta_salida, ruta_logo, iconos=None):
    """Crea un informe PDF unificado con estilo Cynet a partir de los datos extraídos."""
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib.units import inch
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.graphics.shapes import Drawing, Rect
    from reportlab.graphics import renderPDF
    from reportlab.graphics.shapes import Group, String
    from PIL import Image as PILImage
    import io
    
    # Definir colores de Cynet basados en el análisis
    # Color azul Cynet (RGB: 0, 102, 255)
    cynet_blue = colors.Color(0/255, 102/255, 255/255)  # Azul brillante
    cynet_dark = colors.Color(51/255, 51/255, 51/255)   # Gris oscuro
    cynet_light = colors.Color(240/255, 240/255, 240/255)  # Gris claro
    cynet_pink = colors.Color(255/255, 20/255, 147/255)  # Rosa para el escudo
    cynet_teal = colors.Color(0/255, 229/255, 176/255)  # Verde azulado para el engranaje
    
    # Registrar fuentes personalizadas para Cynet
    fonts = registrar_fuentes_cynet()
    font_name = fonts.get('normal', 'Helvetica')
    font_name_bold = fonts.get('bold', 'Helvetica-Bold')
    
    # Crear el documento PDF con orientación horizontal (landscape)
    doc = SimpleDocTemplate(
        ruta_salida, 
        pagesize=landscape(letter),
        leftMargin=0.5*inch,
        rightMargin=0.5*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )
    
    estilos = getSampleStyleSheet()
    
    # Crear estilos personalizados con la apariencia de Cynet
    estilo_titulo = ParagraphStyle(
        'CynetTitle',
        parent=estilos['Heading1'],
        fontSize=22,
        fontName=font_name_bold,
        textColor=cynet_dark,
        alignment=0,  # Alineación izquierda como en los informes originales
        spaceAfter=12
    )
    
    estilo_encabezado = ParagraphStyle(
        'CynetHeading',
        parent=estilos['Heading2'],
        fontSize=16,
        fontName=font_name_bold,
        textColor=cynet_dark,
        alignment=0,
        spaceAfter=6
    )
    
    estilo_subencabezado = ParagraphStyle(
        'CynetSubheading',
        parent=estilos['Heading3'],
        fontSize=14,
        fontName=font_name_bold,
        textColor=cynet_dark,
        spaceAfter=6
    )
    
    estilo_normal = ParagraphStyle(
        'CynetNormal',
        parent=estilos['Normal'],
        fontSize=10,
        fontName=font_name,
        textColor=cynet_dark
    )
    
    # Construir el contenido del documento
    contenido = []
    
    # Verificar y preparar el logo
    try:
        # Verificar que el archivo existe y es una imagen válida
        img = PILImage.open(ruta_logo)
        # Calcular dimensiones adecuadas manteniendo la proporción
        width, height = img.size
        aspect_ratio = width / height
        logo_width = 1.5*inch
        logo_height = logo_width / aspect_ratio
        
        # Usar el logo verificado
        logo_img = Image(ruta_logo, width=logo_width, height=logo_height)
    except Exception as e:
        print(f"Warning: Could not load logo from {ruta_logo}: {e}")
        # Crear un rectángulo azul como reemplazo del logo
        d = Drawing(1.5*inch, 0.5*inch)
        d.add(Rect(0, 0, 1.5*inch, 0.5*inch, fillColor=cynet_blue))
        logo_img = d
    
    # Crear tabla de encabezado con logo y título
    fecha_generacion = datetime.datetime.now().strftime('%d-%b-%Y')
    datos_encabezado = [
        [logo_img, Paragraph("Executive Summary", estilo_titulo)],
        ["", Paragraph(f"Unified Report - Generated: {fecha_generacion}", estilo_normal)]
    ]
    
    tabla_encabezado = Table(datos_encabezado, colWidths=[2*inch, 8*inch])
    tabla_encabezado.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))
    
    contenido.append(tabla_encabezado)
    contenido.append(Spacer(1, 0.25*inch))
    
    # Agregar una tabla resumen para todos los informes
    datos_resumen = [
        ['Report', 'Critical/High Alerts', 'Handled Alerts', 'Affected Files', 'Remediated Files', 'Affected Endpoints', 'Auto. Investigations', 'Response Actions']
    ]
    
    for datos in datos_todos:
        nombre_informe = datos['resumen']['nombre']
        alertas_activadas = datos['malicioso']['alertas_activadas']
        alertas_manejadas = datos['malicioso']['alertas_manejadas']
        archivos_afectados = datos['malicioso']['archivos_afectados']
        archivos_remediados = datos['malicioso']['archivos_remediados']
        endpoints_afectados = datos['malicioso']['endpoints_afectados']
        investigaciones_auto = datos['automatizacion']['investigaciones_auto']
        acciones_respuesta = datos['automatizacion']['acciones_respuesta']
        
        datos_resumen.append([
            nombre_informe,
            alertas_activadas,
            alertas_manejadas,
            archivos_afectados,
            archivos_remediados,
            endpoints_afectados,
            investigaciones_auto,
            acciones_respuesta
        ])
    
    # Calcular totales
    totales = ['TOTAL']
    for i in range(1, 8):
        total = sum(int(fila[i]) for fila in datos_resumen[1:])
        totales.append(str(total))
    
    datos_resumen.append(totales)
    
    # Calcular anchos de columna para que la tabla se ajuste a la página en modo horizontal
    page_width = landscape(letter)[0] - 2*0.5*inch  # Ancho de página horizontal menos márgenes
    col_widths = [2.5*inch]  # Primera columna para el nombre del informe (más ancha)
    remaining_width = page_width - 2.5*inch
    num_other_cols = len(datos_resumen[0]) - 1
    other_col_width = remaining_width / num_other_cols
    for _ in range(num_other_cols):
        col_widths.append(other_col_width)
    
    # Crear la tabla resumen con anchos específicos y estilo Cynet
    tabla_resumen = Table(datos_resumen, repeatRows=1, colWidths=col_widths)
    tabla_resumen.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), cynet_blue),
        ('BACKGROUND', (0, -1), (-1, -1), cynet_light),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), font_name_bold),
        ('FONTNAME', (0, -1), (-1, -1), font_name_bold),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),  # Reducir tamaño de fuente para mejor ajuste
        ('WORDWRAP', (0, 0), (-1, -1), True),  # Permitir ajuste de texto
    ]))
    
    contenido.append(Paragraph("Comparative Summary", estilo_encabezado))
    contenido.append(Spacer(1, 0.1*inch))
    contenido.append(tabla_resumen)
    contenido.append(Spacer(1, 0.25*inch))
    
    # Preparar iconos
    if iconos is None:
        # Crear iconos simples como fallback
        shield_icon = Drawing(0.5*inch, 0.5*inch)
        shield_icon.add(Rect(0, 0, 0.5*inch, 0.5*inch, fillColor=cynet_pink, strokeColor=colors.black))
        
        gear_icon = Drawing(0.5*inch, 0.5*inch)
        gear_icon.add(Rect(0, 0, 0.5*inch, 0.5*inch, fillColor=cynet_teal, strokeColor=colors.black))
    else:
        # Usar los iconos proporcionados (datos binarios)
        try:
            # Crear archivos temporales para los iconos
            shield_buffer = BytesIO(iconos['shield'])
            gear_buffer = BytesIO(iconos['gear'])
            
            # Crear imágenes a partir de los datos binarios
            shield_icon = Image(shield_buffer, width=0.5*inch, height=0.5*inch)
            gear_icon = Image(gear_buffer, width=0.5*inch, height=0.5*inch)
        except Exception as e:
            print(f"Warning: Could not load icons: {e}")
            # Crear iconos simples como fallback
            shield_icon = Drawing(0.5*inch, 0.5*inch)
            shield_icon.add(Rect(0, 0, 0.5*inch, 0.5*inch, fillColor=cynet_pink, strokeColor=colors.black))
            
            gear_icon = Drawing(0.5*inch, 0.5*inch)
            gear_icon.add(Rect(0, 0, 0.5*inch, 0.5*inch, fillColor=cynet_teal, strokeColor=colors.black))
    
    # Agregar secciones detalladas para cada informe
    for datos in datos_todos:
        nombre_informe = datos['resumen']['nombre']
        rango_fechas = datos['resumen']['rango_fechas']
        generado = datos['resumen']['generado']
        
        # Crear un recuadro con fondo gris claro para el título del informe (estilo Cynet)
        datos_titulo_informe = [[Paragraph(f"Report: {nombre_informe}", estilo_encabezado)]]
        tabla_titulo_informe = Table(datos_titulo_informe, colWidths=[page_width])
        tabla_titulo_informe.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), cynet_light),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        
        contenido.append(tabla_titulo_informe)
        contenido.append(Spacer(1, 0.1*inch))
        contenido.append(Paragraph(f"Date Range: {rango_fechas}", estilo_normal))
        contenido.append(Paragraph(f"Generated: {generado}", estilo_normal))
        contenido.append(Spacer(1, 0.1*inch))
        
        # Sección de Detecciones Maliciosas con estilo Cynet e icono
        # Crear tabla para el título con icono
        datos_titulo_malicioso = [[shield_icon, Paragraph("Malicious Detections and Preventions", estilo_subencabezado)]]
        tabla_titulo_malicioso = Table(datos_titulo_malicioso, colWidths=[0.6*inch, page_width-0.6*inch])
        tabla_titulo_malicioso.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LINEABOVE', (0, 0), (-1, 0), 2, cynet_blue),
        ]))
        
        contenido.append(tabla_titulo_malicioso)
        contenido.append(Spacer(1, 0.1*inch))
        
        datos_maliciosos = [
            ['Metric', 'Value'],
            ['Critical/high alerts triggered', datos['malicioso']['alertas_activadas']],
            ['Critical/high alerts handled', datos['malicioso']['alertas_manejadas']],
            ['Affected files', datos['malicioso']['archivos_afectados']],
            ['Remediated files', datos['malicioso']['archivos_remediados']],
            ['Affected endpoints', datos['malicioso']['endpoints_afectados']]
        ]
        
        # Ajustar anchos de columna para la tabla de datos maliciosos
        tabla_maliciosos = Table(datos_maliciosos, colWidths=[4*inch, 1*inch])
        tabla_maliciosos.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), cynet_blue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), font_name_bold),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        contenido.append(tabla_maliciosos)
        contenido.append(Spacer(1, 0.2*inch))
        
        # Sección de Automatización con estilo Cynet e icono
        datos_titulo_auto = [[gear_icon, Paragraph("Automation", estilo_subencabezado)]]
        tabla_titulo_auto = Table(datos_titulo_auto, colWidths=[0.6*inch, page_width-0.6*inch])
        tabla_titulo_auto.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LINEABOVE', (0, 0), (-1, 0), 2, cynet_blue),
        ]))
        
        contenido.append(tabla_titulo_auto)
        contenido.append(Spacer(1, 0.1*inch))
        
        datos_automatizacion = [
            ['Metric', 'Value'],
            ['Automatic investigations', datos['automatizacion']['investigaciones_auto']],
            ['Response actions', datos['automatizacion']['acciones_respuesta']]
        ]
        
        # Ajustar anchos de columna para la tabla de automatización
        tabla_automatizacion = Table(datos_automatizacion, colWidths=[4*inch, 1*inch])
        tabla_automatizacion.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), cynet_blue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), font_name_bold),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        contenido.append(tabla_automatizacion)
        contenido.append(Spacer(1, 0.35*inch))
    
    # Agregar pie de página con estilo Cynet
    def pie_pagina(canvas, doc):
        canvas.saveState()
        canvas.setFont(font_name, 8)
        canvas.setFillColor(cynet_dark)
        footer_text = f"Unified Cynet Report - Generated: {fecha_generacion}"
        canvas.drawString(0.5*inch, 0.5*inch, footer_text)
        canvas.drawRightString(landscape(letter)[0] - 0.5*inch, 0.5*inch, f"Page {doc.page}")
        canvas.restoreState()
    
    # Construir el PDF con el pie de página
    doc.build(contenido, onFirstPage=pie_pagina, onLaterPages=pie_pagina)
    
    return ruta_salida

# Función principal
# Función principal
def main():
    """Función principal que ejecuta el proceso completo."""
    print("=" * 80)
    print("  UNIFICADOR DE REPORTES EJECUTIVOS CYNET PDF ")
    print("=" * 80)
    print("\n Este script unifica informes de Cynet en un único reporte unificado.")
    print("Extrae información específica de cada reporte y lo presenta en un formato consolidado.\n")
    
    # Verificar e instalar dependencias
    print("Verificando dependencias...")
    verificar_instalar_dependencias()
    
    # Importar módulos después de verificar dependencias
    import fitz  # PyMuPDF
    import glob
    import re
    from datetime import datetime
    
    # Configurar codificación para consolas Windows
    if os.name == 'nt':
        # Intentar configurar la consola para UTF-8
        try:
            import codecs
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
        except:
            pass  # Si falla, continuamos con la configuración predeterminada
    
    # Definir la ruta predeterminada según el sistema operativo
    if os.name == 'nt':  # Windows
        reports_dir = r"C:\Cynet_Reports"
    else:  # Linux/Mac
        home_dir = os.path.expanduser("~")
        reports_dir = os.path.join(home_dir, "Cynet_Reports")
    
    # Verificar si existe el directorio de informes
    if not os.path.exists(reports_dir):
        print(f"Directorio predeterminado no encontrado: {reports_dir}")
        while True:
            respuesta = input("¿Desea crear este directorio (C), especificar otra ruta (E) o cancelar (X)? ").strip().upper()
            
            if respuesta == 'C':
                try:
                    os.makedirs(reports_dir)
                    print(f"Directorio creado: {reports_dir}")
                    print(f"Por favor, coloque los archivos PDF de Cynet en: {reports_dir}")
                    print("\nPresione Enter para salir...")
                    input()
                    return
                except Exception as e:
                    print(f"Error al crear el directorio {reports_dir}: {e}")
                    # Continúa al caso de especificar otra ruta
            
            if respuesta == 'E':
                nueva_ruta = input("Introduzca la ruta completa donde se encuentran los archivos PDF de Cynet: ").strip()
                
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
                    crear_dir = input("¿Desea crear este directorio? (S/N): ").strip().upper()
                    if crear_dir == 'S':
                        try:
                            os.makedirs(nueva_ruta)
                            print(f"Directorio creado: {nueva_ruta}")
                            print(f"Por favor, coloque los archivos PDF de Cynet en: {nueva_ruta}")
                            print("\nPresione Enter para salir...")
                            input()
                            return
                        except Exception as e:
                            print(f"Error al crear el directorio {nueva_ruta}: {e}")
                    # Vuelve al principio del bucle para pedir otra ruta
            
            elif respuesta == 'X':
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
    patron_fecha = r'(\d+-[A-Za-z]+-\d+)---(\d+-[A-Za-z]+-\d+)'
    
    # Lista para almacenar información de los períodos
    informes_disponibles = []
    
    # Diccionario para traducir nombres de meses
    meses_completos = {
        'Jan': 'Enero', 'Feb': 'Febrero', 'Mar': 'Marzo', 'Apr': 'Abril',
        'May': 'Mayo', 'Jun': 'Junio', 'Jul': 'Julio', 'Aug': 'Agosto',
        'Sep': 'Septiembre', 'Oct': 'Octubre', 'Nov': 'Noviembre', 'Dec': 'Diciembre'
    }
    
    for archivo in pdf_files:
        nombre_archivo = os.path.basename(archivo)
        match = re.search(patron_fecha, nombre_archivo)
        
        if match:
            fecha_inicio = match.group(1)  # 8-Mar-2025
            fecha_fin = match.group(2)     # 8-Apr-2025
            
            # Extraer componentes de las fechas
            try:
                dia_inicio, mes_inicio_abr, año_inicio = fecha_inicio.split('-')
                dia_fin, mes_fin_abr, año_fin = fecha_fin.split('-')
                
                # Convertir a nombres completos en español
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
                    'archivo': archivo,
                    'periodo': periodo,
                    'fecha_inicio': fecha_inicio,
                    'fecha_fin': fecha_fin,
                    'nombre_archivo': nombre_archivo
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
        periodo = informe['periodo']
        if periodo not in informes_por_periodo:
            informes_por_periodo[periodo] = []
        informes_por_periodo[periodo].append(informe)
    
    # Mostrar períodos disponibles
    print("\nPeríodos disponibles en los informes:")
    periodos = list(informes_por_periodo.keys())
    
    # Tratar de ordenar los períodos cronológicamente
    def get_sort_key(periodo):
        # Intentar extraer año y mes para ordenar
        if ' a ' in periodo:
            # Para períodos como "Marzo a Abril 2025"
            partes = periodo.split(' a ')
            if len(partes) == 2:
                inicio = partes[0]
                if ' ' in inicio:
                    mes, año = inicio.rsplit(' ', 1)
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
        print(f"  {i+1}. {periodo} ({cantidad} informes)")
    
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
    rutas_pdf = [informe['archivo'] for informe in informes_seleccionados]
    
    print(f"\nSe procesarán {len(rutas_pdf)} archivos del período {periodo_seleccionado}:")
    for i, informe in enumerate(informes_seleccionados):
        print(f"  {i+1}. {informe['nombre_archivo']}")
    
    # Verificar si el logo de Cynet existe
    script_dir = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(script_dir, "cynet_logo.png")
    
    if not os.path.exists(logo_path):
        print("Logo de Cynet no encontrado, buscando en ubicaciones alternativas....")
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
                print(f"Found logo at: {logo_path}")
                break
        
        if not os.path.exists(logo_path):
            print("Warning: Logo de Cynet no encontrado. El reporte será generado sin logo.")
            # Usar un placeholder para el logo
            from reportlab.lib.utils import ImageReader
            from PIL import Image, ImageDraw
            
            # Crear un logo placeholder
            img = Image.new('RGB', (300, 100), color=(0, 102, 255))
            d = ImageDraw.Draw(img)
            d.text((20, 40), "CYNET", fill=(255, 255, 255))
            
            # Guardar el logo placeholder
            os.makedirs(os.path.dirname(logo_path), exist_ok=True)
            img.save(logo_path)
            print(f"Created placeholder logo at: {logo_path}")
    
    # Crear iconos embebidos (en lugar de SVG)
    print("Creando íconos...")
    try:
        iconos = crear_iconos_embebidos()
        print("Icons created successfully.")
    except Exception as e:
        print(f"Warning: Could not create icons: {e}")
        iconos = None
    
    # Definir ruta de salida automáticamente con el período en el nombre
    # Reemplazar espacios y caracteres especiales para el nombre de archivo
    nombre_periodo = periodo_seleccionado.replace(' ', '_').replace('/', '-')
    ruta_salida = os.path.join(reports_dir, f"unified_cynet_report_{nombre_periodo}.pdf")
    
    print("\nProcesando archivos PDF...")
    
    # Extraer datos de todos los PDFs
    todos_datos = []
    for ruta in rutas_pdf:
        print(f"Extrayendo data de: {os.path.basename(ruta)}")
        datos = extraer_datos_pdf(ruta)
        todos_datos.append(datos)
        
        # Mostrar las fuentes encontradas (si están disponibles)
        if 'fonts' in datos:
            print(f"Fuentes encontradas en {os.path.basename(ruta)}: {', '.join(datos['fonts'])}")
    
    # Crear el informe unificado con estilo Cynet
    print("\nCreando un informe unificado con la marca Cynet...")
    ruta_final = crear_informe_unificado(todos_datos, ruta_salida, logo_path, iconos)
    
    print(f"\n¡Proceso completado exitosamente!")
    print(f"El informe unificado de Cynet se ha guardado en: {os.path.abspath(ruta_final)}")
    
    print("\nPresione Enter para salir...")
    input()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nError: {str(e)}")
        print("\nSe produjo un error inesperado. Inténtalo de nuevo.")
        print("Si el problema persiste, contacte con el equipo de Optimus.")
        print("\nPresione Enter para salir...")
        input()
