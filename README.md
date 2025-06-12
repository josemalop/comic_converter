# Comic Converter
Basicamente este script lo hice para sustituir en Linux o Cygwin a la aplicación de Windows CbxConverter. Los inicios fueron con bash, pero al final se ha quedado en Python porque lo de las barras de progreso en bash era algo infernal xD.

## Requisitos: 
* **7z**. Descomprime los ZIP/CBZ y genera los CBZ de salida.
* **unrar-nonfree**. Descomprime los RAR/CBR.
* **zip**. Para reparar las cabeceras de algunos ficheros cbz. A veces al descargar galerías con scripts de Tampermonkey las cabeceras se quedan corruptas y el script peta.
* **ImageMagick** (identify, convert y mogrify). Identifica imágenes, reescala y convierte a Webp.
* **pdftoppm** (para convertir los PDF a imágenes).

## Librerías de python:
* **tqdm**
(puede que falte alguna más, si peta al ejecutarse la instalas con pip xD. Cuando haga una instalación nueva completaré esto).

## Configuración:
El script tiene una sección de configuración donde se puede adaptar el funcionamiento, los parámetros más destacables son:

* **CALIDAD_WEBP** (por defecto 75). Calidad de compresión en formato WEBP (a mi me vale para verlo bien en el iPad, cámbialo si quieres).
* **ANCHO_MAXIMO** (por defecto 1366). Ancho máximo de la imagen a generar (ideal para mi iPad, cámbialo si quieres).
* **ALTO_MAXIMO** (por defecto 1366). Alto máximo de la imagen a generar (ideal para mi iPad, cámbialo si quieres).
* **COMPRESION_CBZ** (por defecto ['-tzip', '-mx=9']). Parámetros de 7zip para generar un zip/cbz estandar con máxima compresión.
* **MAX_PARALELO** (por defecto min(multiprocessing.cpu_count() - 1, 8)). El script procesará en paralelo el menor número de comics entre el número de cores de tu ordenador -1 u 8.

## Uso del script:
  `comic_converter.py entrada [salida]`

Busca en la ruta de entrada ficheros CBR, CBZ y PDF, los procesa y los deja en la ruta de salida. 
Si se omite la ruta de salida, crea un directorio "salida" en la ruta de entrada.
El script evita que se procese un fichero 2 veces, si existe en la ruta de salida, no hace nada.

##TODO: 
* Mejorar la documentación xD
