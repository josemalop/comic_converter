Basicamente este script lo hice para sustituir en Linux o Cygwin a la aplicación de Windows CbxConverter.

Requisitos: 
* 7z. Descomprime los ZIP/CBZ y genera los CBZ de salida.
* unrar-nonfree. Descomprime los RAR/CBR.
* ImageMagick (identify y convert). Identifica imágenes, reescala y convierte a Webp.
* pdftoppm (para convertir los PDF a imágenes).

Librerías de python:
* tqdm
(puede que alguna más, si peta al ejecutarse la instalas con pip xD).

El script tiene una sección de configuración donde se puede adaptar el funcionamiento, los parámetros más destacables son:

* 'CALIDAD_WEBP': 75, # Calidad de compresión en formato WEBP
* 'ANCHO_MAXIMO': 1366, # Ancho máximo de la imagen a generar (ideal para Ipad).
* 'ALTO_MAXIMO': 1366, # Alto máximo de la imagen a generar (ideal para Ipad).
* 'COMPRESION_CBZ': ['-tzip', '-mx=9'], # Parámetros de 7zip para generar un zip/cbz estandar con máxima compresión.
* 'MAX_PARALELO': min(multiprocessing.cpu_count() - 1, 8), # Para la concurrencia se usa el menor de los valores (nºcores -1) u 8

Uso del script:
  comic_converter.py entrada [salida]

Busca en la ruta de entrada ficheros CBR, CBZ y PDF, los procesa y los deja en la ruta de salida. Si se omite la ruta de salida, crea un directorio "salida" en la ruta de entrada.
El script evita que se procese un fichero 2 veces, si existe en la ruta de salida, no hace nada.

TODO: Mejorar la documentación xD
