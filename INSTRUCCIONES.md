# GO Arequipa Noticias · Centro editorial independiente (MVP)

**Versión:** prototipo ejecutable para instalar en una computadora o servidor propio. **No está desplegado en internet** ni conectado a Canva/ChatGPT.

## Funciones que están implementadas

1. Consulta RSS configurados y guarda noticias nuevas con fecha, título, fuente y enlace.
2. Filtra a Arequipa (incluye provincias/distritos); noticias nacionales solo pasan por un filtro de sucesos excepcionales y requieren revisión.
3. Evita duplicar URL o titulares casi idénticos.
4. Trabajador que revisa RSS al iniciar y cada hora (minuto 13, zona America/Lima).
5. Redacción por OpenAI API **opcional**; sin clave, prepara borradores básicos y obliga a contrastar los hechos.
6. Panel privado con estados: pendiente, revisada, aprobada, publicada, descartada.
7. Propone una imagen de referencia cuando el RSS o los metadatos públicos la ofrecen, **sin descargarla ni atribuirle derechos de uso**.
8. El editor puede subir foto propia/autorizada, confirmar derechos, escoger entre dos composiciones, exportar JPG vertical de 1080 × 1350 y descargar un TXT con texto y fuente.
9. Telegram opcional: avisa cuando se descubren noticias nuevas; requiere token y chat_id que configura el editor. No incluye autenticación pública.
10. No se conecta con ninguna cuenta de ChatGPT. Datos en `data/noticias.db`; se pueden respaldar y migrar a otro servidor.

## Primer arranque en Windows

Instala Python 3.11 o 3.12 con la opción “Add Python to PATH”. En una terminal abierta en la carpeta del proyecto:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Abre `.env` y cambia `ADMIN_PASSWORD` y `SECRET_KEY` por valores secretos y largos. No los compartas. Puedes generar el segundo con:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

En una terminal:

```powershell
python app.py
```

Abre `http://127.0.0.1:5050` e ingresa con la contraseña configurada.

En **otra** terminal de la misma carpeta:

```powershell
.venv\Scripts\activate
python worker.py
```

Deja ambos procesos encendidos para que el buscador funcione de manera independiente. Si cierras la computadora, el buscador se detiene. Para mantenerlo activo 24/7, instala el sistema en un servidor y ejecuta ambos servicios con un supervisor (o Docker Compose).

## Docker opcional

Con Docker instalado, ejecuta, después de configurar `.env`:

```shell
docker compose up -d --build
```

El panel se expone **solo localmente** en `127.0.0.1:5050` por seguridad. Para ingresar desde cualquier dispositivo, usa un VPS con un proxy HTTPS y autenticación reforzada o una VPN privada. **No expongas directamente el servidor de desarrollo Flask a internet.** Esta primera versión no es una aplicación pública endurecida.

## Inteligencia artificial (opcional)

En `.env`, coloca `OPENAI_API_KEY=...` (desde la plataforma API de OpenAI). La API se cobra aparte de ChatGPT; no es necesaria para ejecutar la búsqueda y la revisión. Sin clave, el copy es deliberadamente incompleto y lo completa un editor tras leer la fuente. No pegues la clave en chats ni repositorios.

**Cuidado:** un texto de IA es un borrador, no una verificación independiente. La verificación editorial debe contemplar fuente original, fecha del acontecimiento y contraste adicional en asuntos sensibles.

## Fuentes de noticias

Edita `config.json` para agregar, activar o desactivar fuentes RSS. Incluí como fuentes iniciales de investigación El Búho, RPP y La República; consulta sus políticas y condiciones antes de redistribuir contenido. El motor solo importa metadatos/extractos para uso editorial: **no está diseñado para republicar artículos completos ni imágenes de terceros**.

**No se utiliza Google News RSS de forma automática** porque sus feeds pueden estar restringidos a uso personal/no comercial; evalúa una API de noticias con licencia comercial si necesitas cobertura más completa. Agrega canales oficiales con permiso de uso o sus RSS verificables. El filtro geográfico es heurístico y puede fallar: revisa las entradas antes de aprobarlas.

## Avisos independientes por Telegram (opcional)

Puedes configurar `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` en `.env` con credenciales de un bot creado por ti en Telegram. El trabajador enviará un resumen con fuentes cuando haya nuevas noticias. Sin esas variables, todo sigue funcionando desde el panel y no se envían mensajes. Los avisos son para revisión, **no son publicaciones automáticas**.

## Fotos de alta calidad y Canva Gratis

El motor busca fotografías de referencia en RSS o `og:image` de las noticias. Estas imágenes pueden no tener resolución suficiente o permisos de reproducción. Abre el enlace, comprueba los derechos y consigue el original en alta resolución del autor o fuente autorizada. Sube la foto desde la ficha de noticia (ideal 1080 × 1350 px o más). El editor debe declarar el crédito y confirmar permiso.

Se incluyen dos **composiciones originales parecidas al estilo de las capturas**, no ediciones directas de los archivos de Canva. Para un resultado idéntico con tu logo, exporta tu logo como `assets/logo_go.png` (PNG transparente). Para replicar al píxel tus dos plantillas, necesitaremos los fondos sin textos ni fotografías, exportados de Canva. Canva Gratis **no incluye** Autofill API/Crear en lote como recurso del sistema; el panel genera JPG independiente o textos para pegar a mano en Canva.

## Pasos para publicar (control humano obligatorio)

1. Abre el panel y revisa los hechos y la fecha de cada noticia.
2. Edita cintillo, título, bajada y copy; verifica acusaciones, cifras y fuentes.
3. Selecciona Modelo 1 (foto principal) o Modelo 2 (foto principal más círculo opcional).
4. Adjunta una foto propia o licenciada, registra el crédito y marca permisos.
5. Cambia el estado a `aprobada` y guarda.
6. Descarga la imagen JPG y el TXT; publica manualmente.
7. Cambia el estado a `publicada` para evitar confusiones.

## Limitaciones actuales

- No existe búsqueda universal garantizada: solo RSS configurados y fotografías de sus metadatos. No se comprobó aquí el acceso real a internet de esos RSS.
- No verifica automáticamente toda la veracidad de una noticia ni las licencias de las fotografías.
- No publica ni rellena tus diseños en Canva directamente.
- No está montado en la nube ni funcionará si apagas el equipo donde lo ejecutes.
- El panel usa contraseña única; antes de habilitar acceso externo requiere HTTPS, control de usuarios y otras medidas de seguridad.
- La primera versión debe probarse con feeds reales desde una computadora con internet antes de considerarse lista para producción.

## Migración a otra cuenta de ChatGPT o a otro computador

No dependes de ChatGPT. Copia esta carpeta y la base `data/` a otro servidor. Configura los secretos y ejecuta los servicios. Los datos y el historial seguirán contigo. Si le das acceso a otra persona, usa una cuenta editorial propia; evita compartir credenciales de ChatGPT prestadas.

**Canva original:** https://canva.link/qb97kyldbrboag9
