# GO Arequipa Noticias V6 — Editor visual y logotipo real

Esta actualización mantiene la búsqueda horaria, la conexión local de Gemini, los cinco hashtags, las fichas y la base de datos de la V5. **No necesita Canva Pro**: modifica el generador JPG del propio programa, no la plantilla en la nube de Canva.

## Novedades

- Se incluye el logo oficial de GO Arequipa Noticias que proporcionó el propietario, convertido de JPEG a PNG con el exterior transparente. El programa lo copia a `GO_Arequipa_Datos/assets/logo_go.png` si todavía no existe otro logotipo personalizado.
- Nueva sección **Logo del medio** en la barra superior, para reemplazar el logo después de la instalación.
- Editor gráfico con encuadre de la foto principal y la foto circular en el Modelo 2: posición horizontal, vertical, zoom de 1x a 3x, botones para centrar.
- Vista previa sin descargar ni aprobar: permite cambiar la imagen y el contenido antes de exportar, e identifica la previsualización como no publicable.
- Persistencia por noticia en SQLite de los seis parámetros fotográficos. Se añade una migración automática sin eliminar noticias anteriores.
- Exportación JPG 1080 x 1350 con el logo auténtico. Se mantienen los requisitos de aprobación y permiso de publicación de fotografías.
- Las fotografías se guardan localmente. La herramienta **no** actualiza de forma automática diseños editables de Canva; en Canva Gratis seguirás usando el JPG exportado o la edición manual.

## Actualizar desde V5 en Windows (conservando todo)

1. Cierra el programa, incluida su ventana de consola.
2. Haz una copia de seguridad de la carpeta `GO_Arequipa_Datos` (y no compartas `.env` ni `ACCESO_INICIAL.txt`).
3. Descomprime el ZIP de parche **en tu computadora**. Sube a la raíz del mismo repositorio GitHub los archivos y carpetas descomprimidos, **incluida `.github`**.
4. Comprueba que `.github/workflows/compilar-windows.yml` contenga `--add-data "assets;assets"`. Ese paso es esencial para incorporar el logo en el ejecutable.
5. Ejecuta **Actions → Crear GO Arequipa Noticias EXE → Run workflow**, usando la rama `main`. No uses `Re-run jobs` de una ejecución antigua.
6. Si la compilación acaba en verde, descarga el artifact `.exe`. Sustituye solo el ejecutable anterior, en la misma carpeta. **No borres `GO_Arequipa_Datos`.**
7. Abre el panel y verifica que diga **Versión: 6.0 - Editor visual + logo oficial**.
8. En una noticia, sube la foto principal y, si usarás el Modelo 2, sube otra para el círculo. Elige Modelo 2 en el formulario principal, ajusta los deslizadores y usa **Actualizar vista previa**. El guardado automático conserva los controles.
9. Para exportar el JPG final debes marcar los derechos de la fotografía y aprobar la noticia desde la ficha. Se necesita revisión editorial antes de publicar.

La opción **Centrar** ajusta el recorte hacia el centro o tercio superior según el campo. No se realiza reconocimiento de rostros; verifica visualmente que cabeza y rostro estén completos.

## Privacidad y operación

- El logo y las fotografías se almacenan únicamente en tu computadora.
- La clave API Gemini permanece en `GO_Arequipa_Datos/.env` y **no** debe subirse a GitHub.
- Ejecutable compilado en GitHub Actions; no hace falta instalar Python en la PC final.
- Se han ejecutado pruebas de sintaxis, recorte, logo y JPG en Linux; el funcionamiento completo de la web y de Windows debe validarse en GitHub y en tu equipo.
