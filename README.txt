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
