# GO Arequipa Noticias — Edición portátil para Windows

Este paquete es el **proyecto de compilación** para un ejecutable `GO_Arequipa_Noticias.exe` de Windows 10/11 de 64 bits. **El archivo `.exe` no está incluido ni se compiló aquí**: se prepara para compilar con un runner `windows-latest` de GitHub Actions o desde una PC Windows con Python instalado (solo en el equipo de compilación).

## Uso previsto: sin instalaciones en la PC del editor

La compilación usa PyInstaller `--onefile` para empaquetar Python y sus dependencias. El usuario final **no necesita instalar Python, Docker, librerías, ni tener una cuenta de ChatGPT**. Una vez obtenido el `.exe`, descomprime si llega en ZIP y ábrelo con doble clic. La aplicación abre el navegador con el panel en `http://127.0.0.1:5050` (o un puerto local alternativo si 5050 está ocupado).

Los primeros datos y credenciales se guardan en la carpeta `GO_Arequipa_Datos` junto al EXE si hay permisos de escritura, o en `%LOCALAPPDATA%\GO_Arequipa_Noticias` si no. **No borres esa carpeta al actualizar el EXE**: contiene la base de datos, las fotos y `config.json`.

## Compilar sin instalar software en tu computadora

1. Abre [GitHub](https://github.com/new) y crea un repositorio *privado*.
2. Extrae este paquete en tu computadora y sube todo el contenido, incluidas las subcarpetas, al repositorio. Comprueba que exista `.github/workflows/compilar-windows.yml`.
3. En la pestaña **Actions**, habilita Actions si GitHub te lo solicita.
4. Selecciona el flujo **Crear GO Arequipa Noticias EXE** → **Run workflow**.
5. Cuando termine correctamente, descarga **GO_Arequipa_Noticias_Portable_Windows** en **Artifacts**, descomprime y abre `GO_Arequipa_Noticias.exe`.

La acción compila en Windows y realiza una prueba de arranque con HTTP 200 del panel de login. Si falla, **no se debe usar como ejecutable verificado**: revisa el registro de Actions. Las horas de compilación gratuita dependen del plan y las políticas de GitHub.

## Alternativa para una PC de compilación que tenga Python

Ejecuta `compilar_windows.bat` en Windows con Python 3.12 instalado. **Este paso solo es para la PC que compila**, no para quien utiliza el EXE.

## Primera ejecución

Al abrir el ejecutable:

1. Se crea `GO_Arequipa_Datos\config.json` desde los valores iniciales.
2. Se crea un `.env` con contraseña y clave de sesión aleatorias; **no se usan contraseñas universales**.
3. Se crea `GO_Arequipa_Datos\ACCESO_INICIAL.txt`, donde puedes consultar la contraseña local. El archivo **no debe compartirse**.
4. El navegador abre el panel privado; los datos se guardan en `GO_Arequipa_Datos\data`.
5. La búsqueda comienza y se repite cada 60 minutos mientras la aplicación esté abierta. El motor intenta traer metadatos RSS; no promete noticias nuevas en cada hora.
6. Puedes configurar las fuentes editando `GO_Arequipa_Datos\config.json` y reiniciando el EXE.

## Identidad y publicaciones

El generador JPG incorpora dos modelos originales basados en las capturas proporcionadas, con salida 1080×1350. Para usar el logotipo auténtico de GO Arequipa, coloca un PNG transparente como `GO_Arequipa_Datos\assets\logo_go.png`. Para una reproducción exacta de Canva todavía se necesitan los fondos sin textos ni fotografías. Canva Gratis no dispone de la integración de Autofill utilizada en flujos de producción de planes superiores; **este ejecutable no edita la plantilla alojada en Canva**.

Las imágenes del RSS son **referencias**, no fotografías descargadas listas para publicar. Verifica resolución, derechos y atribución antes de subir la foto a la ficha. La aprobación periodística sigue siendo humana.

## IA opcional

Agrega `OPENAI_API_KEY` a `GO_Arequipa_Datos\.env` para generar borradores más completos; la cuenta API de OpenAI es independiente de ChatGPT y puede tener costo. **No subas `.env` a GitHub**. Si no configuras IA, funciona la ingesta y la revisión con borradores simples.

## Seguridad, privacidad y alcance

- Se enlaza únicamente a `127.0.0.1`, no abre acceso público a Internet.
- El panel tiene una contraseña local. No es una plataforma multiusuario endurecida para exponer sin HTTPS.
- Se depende de internet para recibir noticias. Los RSS y la redacción no fueron verificados aquí en funcionamiento real.
- La base de datos permanece en tu PC. Para cambiar de PC, cierra la aplicación y copia la carpeta completa `GO_Arequipa_Datos`.
- Apagar la PC detiene las búsquedas. Para funcionar 24/7 sin PC encendida, instala el sistema en un servidor o servicio continuo.
- Es una **primera versión técnica**, no una versión final plenamente desplegada ni probada en la PC del usuario.


### Versión 4.0 — Cintillos dinámicos
Lee `ACTUALIZACION_V4_LEEME.txt`. Las noticias sin IA usan etiquetas temáticas y borradores breves. La API es opcional para redactar textos completos a partir del contenido fuente. Requiere revisión antes de publicar.


### Versión 4.1 — Copys normalizados
- Quita del copy la frase interna «Información pendiente de contraste editorial». El aviso de verificación sigue visible en la interfaz.
- Genera exactamente cinco hashtags relevantes al final de cada copy, aparte de la etiqueta de apertura #Arequipa | o #Perú |.
- Los copys de noticias pendientes o revisadas se normalizan al iniciar la app; las noticias aprobadas/publicadas se mantienen intactas.
- El servidor también normaliza los copys al pulsar Guardar revisión y al redactar con IA.
- Sin OpenAI API, los borradores siguen siendo breves y requieren revisión; las etiquetas no equivalen a verificación.

## Versión 5.0 — conectar Gemini sin instalar nada en Windows

En el panel web, después de iniciar sesión, abre **Configurar Gemini**, pega la clave de Google AI Studio, elige `gemini-2.5-flash-lite`, y selecciona **Guardar y probar conexión**. Si la prueba confirma acceso, abre una noticia y pulsa **Generar nuevos textos para esta noticia**. El motor también intentará usar Gemini en las noticias nuevas de cada revisión horaria.

- La clave no está dentro del código, del ZIP ni del EXE: se guarda de forma local en `GO_Arequipa_Datos/.env` junto al ejecutable (o en AppData si la carpeta no permite escritura). Nunca subas esta carpeta a GitHub.
- Si se agota la cuota gratuita o falla Gemini, el programa solo genera un borrador local más breve; no debes tratarlo como texto listo para publicar.
- El modelo y su nivel gratuito pueden variar por cuenta y región; comprueba los límites actuales en [Google AI Studio](https://aistudio.google.com/).
- Si compartiste una captura donde se veía tu clave, lo recomendable es revocarla y crear otra antes de usarla.
- Ninguna fuente ni fotografía queda verificada por la IA automáticamente. El editor debe revisar hechos, fechas, atribuciones y permisos antes de aprobar.
