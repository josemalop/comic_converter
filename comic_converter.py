#!/usr/bin/env python3
"""
Comic Converter 0.1
- Script para sustituir en Linux o Cygwin a la aplicación de Windows CbxConverter.

(c) 2025 Josema
"""

import os
import sys
import time
import shutil
import subprocess
import tempfile
import multiprocessing
import concurrent.futures
import unicodedata
import argparse
from datetime import timedelta
from pathlib import Path
from typing import List, Dict, Any
import mimetypes
from tqdm import tqdm
from multiprocessing import Lock

os.environ['PYTHONIOENCODING'] = 'utf-8'
print_lock = Lock()

# Configuración de colores para mensajes
class Colors:
    VERDE = '\033[0;32m'
    AMARILLO = '\033[1;33m'
    ROJO = '\033[0;31m'
    AZUL = '\033[0;34m'
    CYAN = '\033[0;36m'
    MAGENTA = '\033[0;35m'
    RESET = '\033[0m'

# Configuración global
CONFIG: Dict[str, Any] = {
    'CALIDAD_WEBP': 75,
    'ANCHO_MAXIMO': 1366,
    'ALTO_MAXIMO': 1366,
    'COMPRESION_CBZ': ['-tzip', '-mx=9'],
    'MAX_PARALELO': min(multiprocessing.cpu_count() - 1, 8), # Para la concurrencia se usa el menor de los valores (nºcores -1) u 8
    'DIR_ENTRADA': Path.cwd(),
    'DIR_SALIDA': Path.cwd() / 'salida',
    'NOMBRE_MAXIMO': 55,  # Máximo de caracteres para mostrar el nombre de archivo
    'DESC_ANCHO_BARRA': 55  # ← ancho fijo para la barra de imágenes
}

def verificar_dependencias():
    """Verifica que todas las dependencias necesarias estén instaladas"""
    dependencias = ['7z', 'identify', 'convert', 'unrar-nonfree', 'pdftoppm']
    faltantes = []
    for cmd in dependencias:
        try:
            subprocess.run([cmd, '--version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            faltantes.append(cmd)
    if faltantes:
        print(f"{Colors.ROJO}Error: Dependencias faltantes: {', '.join(faltantes)}{Colors.RESET}")
        sys.exit(1)

def ancho_visible(texto: str) -> int:
    """Calcula el ancho visible (descontando caracteres de ancho doble o combinados)"""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in texto)

def ajustar_desc(nombre: str, ancho_objetivo: int) -> str:
    """Recorta y ajusta el nombre para tener un ancho visual alineado"""
    if ancho_visible(nombre) > ancho_objetivo:
        # Recorte suave con '...' en lugar de '…'
        base = nombre[:ancho_objetivo - 10]
        final = nombre[-6:]
        nombre = f"{base}...{final}"
    # Rellenar con espacios hasta igualar el ancho visual
    while ancho_visible(nombre) < ancho_objetivo:
        nombre += " "
    return nombre

def mostrar_progreso(archivo: Path, etapa: str, mensaje: str, color_etapa: str = Colors.CYAN):
    """
    Muestra un mensaje de progreso alineado:
    - recorta el nombre si es largo (inicio + '…' + últimos 7),
    - lo ajusta a un ancho fijo (DESC_ANCHO_BARRA),
    - y luego muestra el mensaje alineado a la derecha.
    """
    nombre_original = archivo.name
    nombre_max = CONFIG.get('NOMBRE_MAXIMO', 50)
    ancho_desc = CONFIG.get('DESC_ANCHO_BARRA', 35)  # por ejemplo: 35 columnas
    # Si el nombre es muy largo, recortarlo
    if len(nombre_original) > ancho_desc:
        inicio = nombre_original[:ancho_desc - 8]
        fin = nombre_original[-7:]
        nombre_recortado = inicio + '…' + fin
    else:
        nombre_recortado = nombre_original
    nombre_ajustado = nombre_recortado.ljust(ancho_desc)
    with print_lock:
        tqdm.write(
            f"{time.strftime('[%H:%M:%S]')} "
            f"{color_etapa}{etapa.ljust(10)}{Colors.RESET} "
            f"{nombre_ajustado} {mensaje}"
        )

def detectar_tipo_archivo(archivo: Path) -> str:
    """Determina el tipo de archivo usando magic numbers"""
    try:
        result = subprocess.run(['file', '--mime-type', '-b', str(archivo)], 
                              capture_output=True, text=True, check=True)
        mime_type = result.stdout.strip().lower()
        
        if 'zip' in mime_type:
            return 'zip'
        elif 'rar' in mime_type:
            return 'rar'
        elif 'pdf' in mime_type:
            return 'pdf'
        elif any(x in mime_type for x in ['jpeg', 'jpg', 'png', 'tiff', 'bmp', 'webp', 'gif']):
            return 'image'
        return 'unknown'
    except subprocess.CalledProcessError:
        return 'unknown'

def convertir_pdf(pdf: Path, temp_dir: Path, archivo: Path) -> bool:
    """Convierte un PDF a imágenes PNG"""
    try:
        result = subprocess.run(['pdfinfo', str(pdf)], capture_output=True, text=True, check=True)
        total_paginas = int(next(line.split()[1] for line in result.stdout.splitlines() 
                               if line.startswith('Pages:')))
        mostrar_progreso(archivo, "PDF", f"Convirtiendo {total_paginas} páginas...")
        for pagina in tqdm(range(1, total_paginas + 1), desc=archivo.name, unit="pág"):
            subprocess.run(['pdftoppm', '-png', '-f', str(pagina), '-l', str(pagina), 
                          str(pdf), str(temp_dir / f"page_{pagina:03d}")], 
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(['mogrify', '-format', 'png', '-quality', '90', str(temp_dir / '*.png')], 
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError as e:
        color_final = Colors.ROJO
        mostrar_progreso(archivo, "ERROR", f"Error PDF: {e}", color_etapa=color_final)
        return False

def procesar_imagen(imagen: Path, archivo_origen: Path) -> bool:
    """Convierte una imagen a WebP con las configuraciones adecuadas"""
    try:
        # Eliminar imagen si está vacía (0 bytes)
        if imagen.stat().st_size == 0:
            mostrar_progreso(imagen, "AVISO", "Eliminada imagen de 0 bytes", Colors.AMARILLO)
            imagen.unlink(missing_ok=True)
            return False
        result = subprocess.run(['identify', '-format', '%w %h', str(imagen)], 
                               capture_output=True, text=True, check=True)
        ancho, alto = map(int, result.stdout.strip().split())
        resize = []
        if ancho > CONFIG['ANCHO_MAXIMO'] or alto > CONFIG['ALTO_MAXIMO']:
            resize = ['-resize', f"{CONFIG['ANCHO_MAXIMO']}x{CONFIG['ALTO_MAXIMO']}>"]
        output_path = imagen.parent / f"cc_{imagen.stem}.webp"
        cmd = ['convert', str(imagen), '-format', 'webp', '-quality', str(CONFIG['CALIDAD_WEBP'])] + resize + [str(output_path)]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        imagen.unlink()
        return True
    except (subprocess.CalledProcessError, ValueError) as e:
        color_final = Colors.ROJO
        mostrar_progreso(archivo_origen, "ERROR", f"Error imagen: {e}", color_etapa=color_final)
        return False

def crear_estructura_salida(archivo_entrada: Path) -> Path:
    """Crea la estructura de directorios de salida manteniendo la jerarquía"""
    ruta_relativa = archivo_entrada.relative_to(CONFIG['DIR_ENTRADA']).parent
    ruta_salida = CONFIG['DIR_SALIDA'] / ruta_relativa
    ruta_salida.mkdir(parents=True, exist_ok=True)
    return ruta_salida

def limpiar_directorio(temp_dir: Path):
    """Elimina archivos no deseados del directorio temporal"""
    for mac_dir in temp_dir.glob('**/__MACOSX'):
        shutil.rmtree(mac_dir, ignore_errors=True)
    patrones_no_deseados = ['.DS_Store', '*.db', '*.txt', '*.url', 'Thumbs.db']
    for patron in patrones_no_deseados:
        for f in temp_dir.glob(f'**/{patron}'):
            try:
                f.unlink()
            except OSError:
                pass

def procesar_archivo(archivo: Path) -> bool:
    """Función principal que procesa cada archivo individual"""
    dir_salida = crear_estructura_salida(archivo)
    archivo_salida = dir_salida / f"{archivo.stem}.cbz"
    if archivo_salida.exists():
        mostrar_progreso(archivo, "OMITIDO", "Archivo ya existe")
        return True
    mostrar_progreso(archivo, "INICIADO", "")
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        tipo_archivo = detectar_tipo_archivo(archivo)
        try:
            if tipo_archivo == 'zip':
                # Verificar integridad del archivo con 7z t
                test_result = subprocess.run(
                    ['7z', 't', str(archivo)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                if test_result.returncode != 0:
                    color_final = Colors.ROJO
                    mostrar_progreso(archivo, "ERROR", "Archivo corrupto o ilegible con 7z", color_etapa=color_final)
                    return False
                # Copiar archivo a nombre temporal seguro
                tmp_archivos_dir = temp_dir_path / "_seguro"
                tmp_archivos_dir.mkdir(parents=True, exist_ok=True)
                nombre_seguro = f"tempfile_{os.getpid()}.cbz"
                ruta_segura = tmp_archivos_dir / nombre_seguro
                shutil.copy2(archivo, ruta_segura)
                # Extraer desde la ruta temporal
                subprocess.run(
                    ['7z', 'x', '-y', f'-o{temp_dir_path}', str(ruta_segura)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True
                )
            elif tipo_archivo == 'rar':
                subprocess.run(['unrar-nonfree', 'x', '-y', '-idq', str(archivo), str(temp_dir_path)], 
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            elif tipo_archivo == 'pdf':
                if not convertir_pdf(archivo, temp_dir_path, archivo):
                    return False
            elif tipo_archivo == 'image':
                shutil.copy(archivo, temp_dir_path / archivo.name)
            else:
                color_final = Colors.ROJO
                mostrar_progreso(archivo, "ERROR", "Tipo no soportado", color_etapa=color_final)
                return False
            limpiar_directorio(temp_dir_path)
            # Procesar todas las imágenes encontradas
            imagenes = []
            for ext in ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tif', '*.tiff', '*.webp', '*.gif']:
                imagenes.extend(temp_dir_path.rglob(ext))
                imagenes.extend(temp_dir_path.rglob(ext.upper()))
            if not imagenes:
                color_final = Colors.ROJO
                mostrar_progreso(archivo, "ERROR", "No hay imágenes", color_etapa=color_final)
                return False
            nombre_original = archivo.name
            nombre_max = CONFIG.get('NOMBRE_MAXIMO', 50)
            ancho_desc = CONFIG.get('DESC_ANCHO_BARRA', 35)
            nombre = archivo.name
            # Recortar si es necesario
            if len(nombre) > nombre_max and nombre_max > 10:
                inicio = nombre[:nombre_max - 8]
                fin = nombre[-7:]
                nombre = inicio + '…' + fin
            ancho_objetivo = CONFIG.get("DESC_ANCHO_BARRA", 35)
            nombre_barra = ajustar_desc(archivo.name, ancho_objetivo)
            desc_barra = f"{nombre_barra}"  # sin emoji ni ANSI
            #nombre_barra = f"🖼 {nombre}".ljust(ancho_desc)
            total_imagenes = len(imagenes)
            # Mostrar barra de imágenes con nombre recortado
            for img in tqdm(
                imagenes,
                desc=desc_barra,
                unit="img",
                bar_format="{desc} |{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]",
                colour="cyan",
                leave=False
            ):
                procesar_imagen(img, archivo)
            # Limpiar nombres con espacios al principio/final (archivos y carpetas)
            for path in sorted(temp_dir_path.rglob('*'), key=lambda p: -len(p.parts)):
                nombre_limpio = path.name.strip()
                if nombre_limpio != path.name:
                    nuevo_path = path.with_name(nombre_limpio)
                    if not nuevo_path.exists():
                        path.rename(nuevo_path)
            # Comprimir a CBZ
            archivos_a_comprimir = [
                f.relative_to(temp_dir_path)
                for f in temp_dir_path.rglob('*')
                if f.is_file() and "_seguro" not in str(f)
            ]
            if archivos_a_comprimir:
                cmd = ['7z', 'a'] + CONFIG['COMPRESION_CBZ'] + [str(archivo_salida)] + [str(f) for f in archivos_a_comprimir]
                subprocess.run(
                    cmd,
                    cwd=temp_dir_path,  # <- esto es obligatorio
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True
                )
            tamaño_entrada = archivo.stat().st_size
            tamaño_salida = archivo_salida.stat().st_size
            def format_mb(size_bytes):
                return f"{size_bytes / (1024 ** 2):.1f} MB"
            if tamaño_salida > tamaño_entrada:
                diff_pct = ((tamaño_salida - tamaño_entrada) / tamaño_entrada) * 100
                cambio = f"↑ +{diff_pct:.1f}%"
                color_final = Colors.AMARILLO
            else:
                diff_pct = ((tamaño_entrada - tamaño_salida) / tamaño_entrada) * 100
                cambio = f"↓ -{diff_pct:.1f}%"
                color_final = Colors.VERDE
            mensaje_final = (
                f"({total_imagenes} img, "
                f"{format_mb(tamaño_entrada)} → {format_mb(tamaño_salida)}, {cambio})"
            )
            mostrar_progreso(archivo, "COMPLETADO", mensaje_final, color_etapa=color_final)
            return True
        except subprocess.CalledProcessError as e:
            color_final = Colors.ROJO
            mostrar_progreso(archivo, "ERROR", f"Error proceso: {e}", color_etapa=color_final)
            return False
        if ruta_segura.exists():
            ruta_segura.unlink(missing_ok=True)

def encontrar_archivos() -> List[Path]:
    """Encuentra todos los archivos válidos para procesar"""
    extensiones = ['*.cbz', '*.cbr', '*.pdf', '*.CBZ', '*.CBR', '*.PDF']
    archivos = []
    for ext in extensiones:
        archivos.extend(CONFIG['DIR_ENTRADA'].rglob(ext))
    # Filtrar archivos que ya están en el directorio de salida
    dir_salida_str = str(CONFIG['DIR_SALIDA'].resolve())
    return [f for f in archivos if not str(f.resolve()).startswith(dir_salida_str)]

def formatear_tiempo(segundos):
    horas = int(segundos // 3600)
    minutos = int((segundos % 3600) // 60)
    segundos = segundos % 60
    return f"{horas:02d}:{minutos:02d}:{segundos:06.3f}"

def main():
    try:
        print("\033[?25l", end='', flush=True)  # Ocultar cursor
        # Configuración inicial
        parser = argparse.ArgumentParser(description="Conversor de cómics a CBZ")
        parser.add_argument("entrada", help="Directorio de entrada con archivos .cbz/.cbr/.pdf")
        parser.add_argument("salida", nargs="?", help="Directorio de salida (opcional)")
        args = parser.parse_args()

        CONFIG['DIR_ENTRADA'] = Path(args.entrada).resolve()
        CONFIG['DIR_SALIDA'] = Path(args.salida).resolve() if args.salida else CONFIG['DIR_ENTRADA'] / 'salida'

        verificar_dependencias()
        CONFIG['DIR_SALIDA'].mkdir(parents=True, exist_ok=True)
        print(f"{Colors.VERDE}=== CONVERSOR DE CÓMICS ===")
        print(f"Entrada: {CONFIG['DIR_ENTRADA']}")
        print(f"Salida: {CONFIG['DIR_SALIDA']}")
        print(f"Hilos: {CONFIG['MAX_PARALELO']}")
        print("="*CONFIG.get('NOMBRE_MAXIMO', 40) + Colors.RESET)
        tiempo_inicio = time.time()
        archivos = encontrar_archivos()
        if not archivos:
            print(f"{Colors.AMARILLO}No se encontraron archivos para procesar{Colors.RESET}")
            return
        print(f"\nArchivos a procesar: {len(archivos)}")
        # Procesamiento en paralelo con ThreadPoolExecutor
        with concurrent.futures.ThreadPoolExecutor(max_workers=CONFIG['MAX_PARALELO']) as executor:
            resultados = []
            with tqdm(
                total=len(archivos),
                desc=f"{Colors.MAGENTA}📦 Progreso total{Colors.RESET}",
                unit="archivo",
                bar_format="{l_bar}{bar} {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]",
                colour="magenta"
            ) as pbar:
                futures = {executor.submit(procesar_archivo, archivo): archivo for archivo in archivos}
                tamaño_total_entrada = sum(f.stat().st_size for f in archivos)
                tamaño_total_salida = 0  # Lo completaremos después del procesamiento
                for future in concurrent.futures.as_completed(futures):
                    resultados.append(future.result())
                    pbar.update(1)
            # Sumar tamaño total de archivos de salida generados (solo los exitosos)
            for archivo in archivos:
                archivo_salida = crear_estructura_salida(archivo) / f"{archivo.stem}.cbz"
                if archivo_salida.exists():
                    tamaño_total_salida += archivo_salida.stat().st_size
        # Estadísticas finales
        tiempo_total = time.time() - tiempo_inicio
        h, m = divmod(tiempo_total/60, 60)
        m, s = divmod(m, 60)
        print(f"\n{Colors.VERDE}=== RESULTADOS ===")
        print(f"Correctos: {sum(resultados)}")
        print(f"Fallidos: {len(resultados) - sum(resultados)}")
        print(f"Tiempo: {formatear_tiempo(tiempo_total)}")
        ahorro_bytes = tamaño_total_entrada - tamaño_total_salida
        if tamaño_total_entrada > 0:
            ahorro_pct = (ahorro_bytes / tamaño_total_entrada) * 100
        else:
            ahorro_pct = 0.0
        print(f"\n{Colors.CYAN}Ahorro total de espacio: {ahorro_bytes / (1024**2):.2f} MB "
            f"({ahorro_pct:+.1f}%){Colors.RESET}")
        print("="*20 + Colors.RESET)
    finally:
        print("\033[?25h", end='', flush=True)  # Mostrar cursor siempre

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.ROJO}Proceso interrumpido por el usuario{Colors.RESET}")
        print("\033[?25h", end='', flush=True)  # Mostrar cursor siempre
        sys.exit(1)
