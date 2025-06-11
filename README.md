Basicamente este script lo hice para sustituir en Linux o Cygwin a la aplicación de Windows CbxConverter.

Requisitos: 
* 7z. Descomprime los ZIP/CBZ y genera los CBZ de salida.
* unrar-nonfree. Descomprime los RAR/CBR.
* ImageMagick (identify y convert). Identifica imágenes, reescala y convierte a Webp.
* pdftoppm (para convertir los PDF a imágenes).

Librerías de python:
* tqdm
(puede que alguna más, petará al ejecutarse xD).

Uso del script:
comic_converter.py entrada [salida]

Busca en la ruta de entrada ficheros CBR, CBZ y PDF, los procesa y los deja en la ruta de salida. Si se omite la ruta de salida, crea un directorio "salida" en la ruta de entrada.
El script evita que se procese un fichero 2 veces, si existe en la ruta de salida, no hace nada.

TODO: Mejorar la documentación xD
