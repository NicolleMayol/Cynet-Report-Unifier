# Unificador de PDF Cynet

Esta herramienta combina múltiples PDFs de Informes Ejecutivos de Cynet en un único informe unificado. Extrae información clave de cada informe y la presenta en un formato consolidado con una imagen de marca Cynet consistente.

## Características

- Extrae datos críticos de los Informes Ejecutivos de Cynet
- Combina datos de múltiples informes en un único PDF
- Organiza informes por períodos completos (ej: "Marzo a Abril 2025")
- Conserva el estilo visual y la imagen de marca de Cynet
- Crea una tabla resumen para facilitar la comparación entre informes
- Funciona en Windows, macOS y Linux
- Detecta automáticamente la ubicación de los archivos o permite especificar una ruta personalizada

## Requisitos

- Python 3.6 o superior
- El script instalará automáticamente las dependencias de Python requeridas:
  - PyMuPDF (para procesamiento de PDF)
  - ReportLab (para generación de PDF)
  - Pillow (para procesamiento de imágenes)

## Instalación

1. Descargue el release desde GitHub: [https://github.com/NicolleMayol/Cynet-Report-Unifier/releases](https://github.com/NicolleMayol/Cynet-Report-Unifier/releases)
   
   El release contiene todos los archivos necesarios:
   - `cynet_pdf_unifier_fixed.py` (script principal)
   - `run_cynet_unifier_fixed.bat` (lanzador para Windows)
   - `run_cynet_unifier_fixed.sh` (lanzador para macOS/Linux)
   - Opcional: `cynet_logo.png` (para el correcto uso de la marca)

   Los scripts .bat y .sh están disponibles directamente para descargar desde el release de GitHub.

2. Asegúrese de tener Python 3.6+ instalado en su sistema.

## Uso

### Para usuarios de Windows:

1. Descargue los archivos del release de GitHub
2. Haga doble clic en el archivo `run_cynet_unifier_fixed.bat`
3. Siga las instrucciones en pantalla:
   - El script buscará automáticamente los informes de Cynet en `C:\Cynet_Reports`
   - Si no encuentra la carpeta, le permitirá crearla o especificar una ruta personalizada
   - Seleccione el período que desea procesar (ej: "Marzo a Abril 2025")
   - El informe unificado se guardará en la misma carpeta con el nombre del período

### Para usuarios de macOS/Linux:

1. Descargue los archivos del release de GitHub
2. Abra una terminal y navegue hasta la carpeta que contiene los archivos
3. Haga ejecutable el script de shell ejecutando:
   ```
   chmod +x run_cynet_unifier_fixed.sh
   ```
4. Ejecute el script mediante:
   - Haciendo doble clic en `run_cynet_unifier_fixed.sh` (si su gestor de archivos lo permite)
   - Ejecutándolo desde la terminal: `./run_cynet_unifier_fixed.sh`
5. Siga las instrucciones en pantalla (similar a Windows)
   - El script buscará automáticamente los informes de Cynet en `~/Cynet_Reports`
   - Si no encuentra la carpeta, le permitirá crearla o especificar una ruta personalizada

## Estructura de carpetas

Para un funcionamiento óptimo, los informes de Cynet deben seguir esta estructura:

### En Windows:
```
C:\Cynet_Reports\
    ├── ExecutiveReport_Cliente1_8-Mar-2025---8-Apr-2025.pdf
    ├── ExecutiveReport_Cliente2_8-Mar-2025---8-Apr-2025.pdf
    └── ...
```

### En macOS/Linux:
```
~/Cynet_Reports/
    ├── ExecutiveReport_Cliente1_8-Mar-2025---8-Apr-2025.pdf
    ├── ExecutiveReport_Cliente2_8-Mar-2025---8-Apr-2025.pdf
    └── ...
```

**IMPORTANTE**: 
- Los informes DEBEN estar dentro de una carpeta llamada `Cynet_Reports` (en Windows en la raíz `C:\` y en Mac/Linux en el directorio del usuario)
- Si la carpeta no existe, el script ofrecerá crearla o permitirá especificar una ubicación alternativa
- Todos los nombres de archivos deben seguir el formato `ExecutiveReport_[Nombre]_[Fecha-inicio]---[Fecha-fin].pdf`

## Notas

- El script intentará encontrar o crear un logo para el correcto uso de la marca
- Debe tener los PDFs originales de Informes Ejecutivos de Cynet accesibles en su computadora
- El script instalará automáticamente cualquier dependencia faltante

## Solución de problemas

Si encuentra algún problema:

1. Asegúrese de que Python 3.6+ esté instalado y en su PATH del sistema
2. Verifique que tiene acceso a Internet para la instalación de dependencias
3. Compruebe que los nombres de los archivos PDF siguen el formato esperado
4. Verifique que tiene permisos de escritura en el directorio de salida
5. En Windows, si experimenta problemas con caracteres especiales, intente ejecutar el script desde PowerShell o actualice su consola para usar UTF-8

## Resultado

El informe unificado contendrá:
- Una tabla comparativa resumida de todos los informes
- Secciones detalladas para cada informe original
- Estilo e imagen de marca de Cynet consistentes

El informe consolidado se guarda como `unified_cynet_report_[Período].pdf` en el directorio de informes.