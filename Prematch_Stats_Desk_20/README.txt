PREMATCH STATS DESK — últimos 20 partidos reales
================================================

Cómo abrir
----------
Windows: doble clic en INICIAR_PREMATCH_STATS.bat
o en una terminal:

    python3 app.py

Luego abrí http://127.0.0.1:8765

Qué se corrigió
---------------
- SofaScore responde 403 en muchas redes: ya no es la fuente principal.
- ESPN usaba site.api.espn.com (403). Ahora usa site.web.api.espn.com.
- Faltaba la función _is_womens_event (el calendario femenino fallaba en silencio).
- El histórico estaba cortado en 10 partidos.

Datos reales
------------
Al pulsar "Ver estadísticas" la app pide los ÚLTIMOS 20 PARTIDOS FINALIZADOS
del local y del visitante (todas las competiciones), con goles, goles 1T,
remates, tiros a puerta, córners, faltas, amarillas, tackles y offsides
cuando la fuente los entrega.

Fuente principal: FotMob.
Respaldo: SofaScore (si no bloquea) y ESPN.
Un campo ausente queda como "Dato no disponible". No se inventan números.

Horarios del listado: hora de Perú (America/Lima, UTC-5).

Favicon, favoritos y móvil
--------------------------
- Favicon propio en /favicon.svg
- Al añadir un favorito o un equipo a lista negra, debajo aparecen
  sus próximos partidos (siguientes 8 días, calendario FotMob).
- En teléfono la lista pasa a tarjetas: nombres y competición completos.

Subir la app gratis
-------------------
La app es un servidor Python. En la nube usa el puerto de la plataforma:

    HOST=0.0.0.0 PORT=10000 python3 app.py

Opción más simple y gratis: Render
1. Subí la carpeta a GitHub (app.py + bat + README).
2. En https://render.com creá un Web Service gratis.
3. Runtime: Python. Build: vacío. Start: python3 app.py
4. Render asigna PORT solo; la app ya lo lee.

Otras opciones gratis:
- Railway.app (crédito mensual)
- PythonAnywhere (cuenta free, un worker)
- Fly.io (capa gratuita pequeña)

GitHub Pages NO sirve: no ejecuta Python.

Guía PythonAnywhere: abrí PYTHONANYWHERE.txt


CORRECCIÓN PARA RENDER — ESTADÍSTICAS
-------------------------------------
La versión actualizada ya no deja que un fallo de FotMob o del módulo de
tarjetas derribe /api/team-stats. Si FotMob responde 403/5xx, intenta
SofaScore/ESPN y devuelve un estado controlado en lugar de un 502 genérico.

RECOMENDADO EN RENDER: API-FOOTBALL
-----------------------------------
Para evitar depender de una IP compartida que pueda ser bloqueada por
FotMob, la app soporta API-Football como fuente principal cuando existe
la variable de entorno:

    API_FOOTBALL_KEY

En Render:
1. Service -> Environment -> Add Environment Variable.
2. Key: API_FOOTBALL_KEY
3. Value: tu clave de API-Football/API-Sports.
4. Guardá y hacé Manual Deploy -> Deploy latest commit.

No pongas la clave dentro de app.py ni la subas a GitHub.

API-Football obtiene los últimos partidos del equipo y puede recuperar
estadísticas de hasta 20 fixtures en una consulta por lote. Si una
competición no publica una estadística concreta, esa celda queda como
"Dato no disponible"; no se inventan valores.

IMPORTANTE
----------
Render no necesita una configuración especial de proxy para este código.
Debe ejecutarse como Web Service y escuchar HOST=0.0.0.0 y PORT=$PORT,
lo que app.py ya hace. Procfile ya contiene:

    web: python3 app.py

La versión actual también redujo el barrido histórico de FotMob y agregó
reintentos solo para errores transitorios. Un 403 de FotMob activa el
fallback en vez de repetirlo indefinidamente.
