from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import datetime
import random
import json
from PIL import Image, ImageDraw, ImageFont
import time
import hashlib
import io
import base64

app = Flask(__name__)
CORS(app) 

# Carpetas y archivos
CARPETA_ORIGINALES = "static/imagenes_originales"
IMAGEN_ORIGINAL = os.path.join(CARPETA_ORIGINALES, "nequi.jpg")
ARCHIVO_CONFIG = "coordenadas_texto.txt"
ARCHIVO_FUENTE = "font.ttf"  # Nombre del archivo de fuente personalizada

# Configuración
COLOR_TEXTO = (31, 7, 33)  # Morado oscuro (#1f0721)
TAMANO_FUENTE = 40
ESPACIADO_LINEAS = 2.5

# Asegurar que la carpeta de originales exista
os.makedirs(CARPETA_ORIGINALES, exist_ok=True)

# Funciones auxiliares
def generar_referencia():
    """Genera una referencia aleatoria en formato M seguido de un número entre 80000000 y 89999999"""
    return f"M{random.randint(80000000, 89999999)}"

def formatear_fecha(fecha):
    """Formatea la fecha en el formato requerido con salto de línea después de 'a'"""
    dia = fecha.day
    
    # Lista de meses en español
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", 
             "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    mes = meses[fecha.month - 1]
    
    anio = fecha.year
    
    # Determinar si es AM o PM
    hora_24 = fecha.hour
    if hora_24 >= 12:
        ampm = "p. m."
        hora = hora_24 - 12 if hora_24 > 12 else hora_24
    else:
        ampm = "a. m."
        hora = hora_24 if hora_24 > 0 else 12
    
    minutos = fecha.minute
    
    # Formato con salto de línea después de "a"
    return f"{dia} de {mes} de {anio} a\nlas {hora}:{minutos:02d} {ampm}"

def formatear_moneda(valor):
    """Convierte un valor numérico a formato de moneda: $xx.xxx,xx"""
    try:
        # Primero intentar convertir a número (por si es string)
        if isinstance(valor, str):
            # Eliminar caracteres no numéricos excepto punto y coma
            valor_limpio = ''.join(c for c in valor if c.isdigit() or c in '.,')
            # Convertir a número (asumiendo que las comas son decimales)
            valor_limpio = valor_limpio.replace('.', '').replace(',', '.')
            valor_num = float(valor_limpio)
        else:
            valor_num = float(valor)
        
        # Formatear con separador de miles y dos decimales
        valor_entero = int(valor_num)
        # Formatear parte entera con puntos como separadores de miles
        parte_entera = ""
        valor_str = str(valor_entero)
        for i, digito in enumerate(reversed(valor_str)):
            if i > 0 and i % 3 == 0:
                parte_entera = "." + parte_entera
            parte_entera = digito + parte_entera
        
        # Obtener los decimales
        decimales = int((valor_num - valor_entero) * 100 + 0.5)  # Redondeo
        
        # Formato final con coma para decimales
        return f"${parte_entera},{decimales:02d}"
    except:
        # Si hay algún error, devolver el valor original
        return valor

def cargar_configuracion():
    """Carga la configuración de posición desde el archivo"""
    try:
        if os.path.exists(ARCHIVO_CONFIG):
            with open(ARCHIVO_CONFIG, 'r') as f:
                return json.loads(f.read())
    except Exception as e:
        print(f"Error al cargar configuración: {str(e)}")
    
    # Configuración por defecto si no hay archivo o hay error
    return {
        "posicion_y_inicial": 200,
        "posicion_x_offset": 0,
        "ajustes_individuales": [
            {"x": 0, "y": 0},  # Nombre
            {"x": 0, "y": 0},  # Cantidad
            {"x": 0, "y": 0},  # Número
            {"x": 0, "y": 0},  # Fecha/hora
            {"x": 0, "y": 0},  # Referencia
            {"x": 0, "y": 0}   # Estado
        ]
    }
def cargar_fuente(tamano):
    """Carga la fuente personalizada o una alternativa"""
    try:
        # Primero intentar cargar la fuente personalizada
        if os.path.exists(ARCHIVO_FUENTE):
            return ImageFont.truetype(ARCHIVO_FUENTE, tamano)
        
        # Si no existe, intentar con las fuentes del sistema
        fuentes = ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf", "calibri.ttf", "Verdana.ttf"]
        for f in fuentes:
            try:
                return ImageFont.truetype(f, tamano)
            except:
                continue
        
        # Si todo falla, usar la fuente por defecto
        return ImageFont.load_default()
    except:
        return ImageFont.load_default()
# Generar una imagen de comprobante sin guardarla en disco
def generar_imagen_comprobante(para, cuanto, numero):
    # Verificar imagen original
    if not os.path.exists(IMAGEN_ORIGINAL):
        raise Exception(f"No se encuentra la imagen original: {IMAGEN_ORIGINAL}")
    
    # Cargar configuración
    config = cargar_configuracion()
    
    # Formatear datos
    cuanto_formateado = formatear_moneda(cuanto)
    fecha_actual = datetime.datetime.now()
    fecha_hora = formatear_fecha(fecha_actual)
    referencia = generar_referencia()
    
    # Abrir imagen original a tamaño completo
    imagen = Image.open(IMAGEN_ORIGINAL)
    if imagen.mode != 'RGB':
        imagen = imagen.convert('RGB')
    
    # Crear objeto para dibujar
    dibujo = ImageDraw.Draw(imagen)
    
    fuente = cargar_fuente(TAMANO_FUENTE)
    
    # Dimensiones
    ancho, alto = imagen.size
    
    # Obtener posiciones
    posicion_y_inicial = config["posicion_y_inicial"]
    desplazamiento_x = config["posicion_x_offset"]
    ajustes_individuales = config["ajustes_individuales"]
    
    # Textos
    campos = [
        para,                 # Nombre
        cuanto_formateado,    # Cantidad formateada
        numero,               # Número
        fecha_hora,           # Fecha y hora
        referencia,           # Referencia
        "Disponible"          # Estado
    ]
    
    # Escribir textos
    for i, campo in enumerate(campos):
        # Posición Y base
        posicion_y_base = posicion_y_inicial + (i * TAMANO_FUENTE * ESPACIADO_LINEAS)
        
        # Aplicar ajustes individuales
        ajuste_x = ajustes_individuales[i]["x"] if i < len(ajustes_individuales) else 0
        ajuste_y = ajustes_individuales[i]["y"] if i < len(ajustes_individuales) else 0
        
        # Verificar si es el campo de fecha (que contiene salto de línea)
        if i == 3 and "\n" in campo:
            # Separar las dos líneas
            lineas = campo.split("\n")
            
            # Primera línea normal (alineada al centro)
            tam_texto_1 = dibujo.textbbox((0, 0), lineas[0], font=fuente)
            ancho_texto_1 = tam_texto_1[2] - tam_texto_1[0]
            posicion_x_1 = (ancho - ancho_texto_1) // 2 + desplazamiento_x + ajuste_x
            posicion_y_1 = posicion_y_base + ajuste_y
            
            # Segunda línea alineada a la derecha
            tam_texto_2 = dibujo.textbbox((0, 0), lineas[1], font=fuente)
            ancho_texto_2 = tam_texto_2[2] - tam_texto_2[0]
            # Alinear a la derecha usando como referencia la posición final de la primera línea
            posicion_x_2 = posicion_x_1 + ancho_texto_1 - ancho_texto_2
            posicion_y_2 = posicion_y_1 + TAMANO_FUENTE
            
            # Dibujar cada línea por separado
            dibujo.text((posicion_x_1, posicion_y_1), lineas[0], fill=COLOR_TEXTO, font=fuente)
            dibujo.text((posicion_x_2, posicion_y_2), lineas[1], fill=COLOR_TEXTO, font=fuente)
            
        else:
            # Código para textos con expansión a la izquierda
            tam_texto = dibujo.textbbox((0, 0), str(campo), font=fuente)
            ancho_texto = tam_texto[2] - tam_texto[0]
            
            # Cálculo de la posición central y del borde derecho deseado
            punto_central = ancho // 2 + desplazamiento_x
            
            # Para nombre (i==0), cantidad (i==1) y número (i==2), controlar expansión a la izquierda
            if i == 0 or i == 1 or i == 2:
                # Definir la posición X final (borde derecho) que queremos mantener fija
                posicion_final_deseada = punto_central + ajuste_x
                
                # La posición X inicial será la posición final menos el ancho del texto
                posicion_x = posicion_final_deseada - ancho_texto
            else:
                # Para otros elementos, centrar normalmente
                posicion_x = punto_central + ajuste_x - (ancho_texto / 2)
            
            posicion_y = posicion_y_base + ajuste_y
            
            # Escribir
            dibujo.text((posicion_x, posicion_y), str(campo), fill=COLOR_TEXTO, font=fuente)
    
    # En lugar de guardar en disco, guardar en un buffer de memoria
    img_buffer = io.BytesIO()
    imagen.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    
    # Convertir a base64 para enviar en JSON
    img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
    
    return img_base64

# Rutas API
@app.route('/api/generar-comprobante', methods=['POST'])
def api_generar_comprobante():
    try:
        # Obtener datos del request
        data = request.json
        para = data.get('para', '')
        cuanto = data.get('cuanto', '')
        numero = data.get('numero', '')
        
        # Validar datos
        if not para or not cuanto or not numero:
            return jsonify({"success": False, "error": "Faltan datos requeridos"}), 400
        
        # Generar imagen en memoria (base64)
        img_base64 = generar_imagen_comprobante(para, cuanto, numero)
        
        return jsonify({
            "success": True,
            "mensaje": "Comprobante generado exitosamente",
            "imagen_base64": img_base64
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Ruta para probar la API desde un navegador
@app.route('/')
def index():
    return """
    <html>
        <head>
            <title>API Nequi Comprobante</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
                h1 { color: #6200ee; }
                pre { background: #f5f5f5; padding: 10px; border-radius: 5px; }
                .endpoint { background: #e3f2fd; padding: 10px; border-radius: 5px; margin-bottom: 10px; }
            </style>
        </head>
        <body>
            <h1>API Nequi Comprobante</h1>
            <p>Esta API permite generar comprobantes de Nequi personalizados.</p>
            
            <h2>Endpoints disponibles:</h2>
            <div class="endpoint">
                <h3>POST /api/generar-comprobante</h3>
                <p>Genera un comprobante personalizado</p>
                <p><strong>Parámetros (JSON):</strong></p>
                <pre>
{
  "para": "Nombre del destinatario",
  "cuanto": "Cantidad (ej: 50000)",
  "numero": "Número de teléfono (ej: 3001234567)"
}
                </pre>
                <p><strong>Respuesta:</strong></p>
                <pre>
{
  "success": true,
  "mensaje": "Comprobante generado exitosamente",
  "imagen_base64": "iVBORw0KGgoAAAANSUhEUgAAADIA..."
}
                </pre>
            </div>
        </body>
    </html>
    """

# Iniciar la aplicación
if __name__ == '__main__':
    # Verificar que exista la carpeta de imágenes originales y el archivo nequi.jpg
    if not os.path.exists(IMAGEN_ORIGINAL):
        print(f"ADVERTENCIA: La imagen original no existe en {IMAGEN_ORIGINAL}")
        print("Asegúrate de colocar tu plantilla de imagen de Nequi en esta ubicación.")

    # Iniciar el servidor
    app.run(debug=True, host='0.0.0.0', port=5000)