# 🎤 Guion de Demo — BasketStats Analytics

Duración estimada: **8–12 min**. Orden sugerido: intro → carga de datos (admin) → un recorrido por cada perfil → cierre.

---

## 0. Antes de empezar (preparación)

- Tener Docker Desktop abierto y corriendo (la ballena fija).
- Levantar el entorno: `./start.sh` (o `docker compose up`) y abrir `http://localhost:8501`.
- **Dejar la base vacía** si querés mostrar la carga en vivo: `docker compose down -v` antes de levantar.
  (Si preferís ir a lo seguro, cargá los datos antes y mostrá el panel sin correrlo.)
- Tener a mano el usuario `admin` / `admin`.

---

## 1. Apertura (30–45 seg)

> "Buenas. Les presentamos **BasketStats Analytics**, una plataforma web de análisis
> estadístico para básquet europeo —EuroLeague y EuroCup—. La idea es centralizar los
> datos de partidos y jugadores y transformarlos en visualizaciones útiles para la toma
> de decisiones.
>
> El sistema está pensado para **cuatro perfiles de usuario**: entrenador, scout,
> analista deportivo y directivo del club. Cada uno entra con su usuario y ve únicamente
> los dashboards que le sirven a su rol. Además hay un perfil **administrador** que se
> encarga de la carga de datos."

*(Mostrá la pantalla de login con el logo.)*

---

## 2. Login + carga de datos como admin (2–3 min) — *el plato fuerte*

1. Logueate como **admin / admin**.
2. Entrá a la pestaña **Administración**.

> "Lo primero que hace el administrador es cargar los datos. Tenemos un **pipeline** que
> toma los CSV crudos de EuroLeague y EuroCup, los limpia, calcula métricas derivadas
> —como PIR, eFG%, TS%, USG%, AST/TO— y los inserta en una base PostgreSQL."

3. Mostrá el panel: las **métricas de estado** (cuántas filas hay por tabla) y los dos modos.

> "Tenemos dos modos de carga:
> - **Actualizar / Agregar (upsert)**: agrega lo nuevo y actualiza lo existente sin borrar
>   nada. Se puede correr las veces que quieras sin duplicar.
> - **Recarga completa**: borra todo y reconstruye desde cero.
>
> Para la demo usamos la **carga rápida**, que omite los datasets más pesados que no
> alimentan ningún gráfico."

4. Apretá **"Ejecutar pipeline"**. Mientras corre (~1 min):

> "Por detrás, esto ejecuta los scripts de limpieza sobre cada dataset y los carga con
> COPY masivo. Fíjense que actualiza el estado de la base al terminar."

5. Cuando termina, mostrá las métricas actualizadas.

> "Listo: ya tenemos las dos competiciones cargadas. Ahora veamos qué ve cada perfil."

*(Si la carga falla por memoria con todos los datasets, recordá: la carga rápida evita
los play-by-play gigantes, que ningún dashboard usa.)*

---

## 3. Recorrido por perfiles (4–6 min)

> Tip: podés mostrar todo desde el admin (que ve todos los dashboards) o cerrar sesión y
> entrar con cada usuario para enfatizar el control de acceso por rol.

### 🏋️ Entrenador
> "El entrenador se enfoca en el rendimiento individual y las decisiones tácticas."
- **Perfil de Tiro**: elegí un jugador → curva de evolución de FGA, 2PM, 3PM, FTA por
  temporada. "Sirve para ver cómo cambió el estilo ofensivo de un jugador en el tiempo."
- **Consistencia Competitiva**: WinRate por fase + el módulo de **cierre con ventaja en
  Q3** (configurable a +10/+15/+20). "Mide qué tan bien cierra el equipo los partidos
  que va ganando al tercer cuarto."

### 🔍 Scout
> "El scout evalúa y compara perfiles de jugadores."
- **Ranking PIR — Top 10**: barras con el índice de valoración. Cambiá a la vista de
  composición ofensiva/defensiva (barras apiladas).
- **Creación de Juego (AST/TO)**: ranking de asistencias sobre pérdidas, el mapa AST vs
  pérdidas por cuadrantes y la comparativa entre jugadores.

### 📊 Analista Deportivo
> "El analista busca patrones tácticos y eficiencia."
- **Mapa de Aciertos**: shot map de media cancha. Tamaño del círculo = volumen de tiros,
  color = efectividad (rojo/amarillo/verde). Movés el mínimo de intentos por zona en vivo.
- **Comparación de Perfiles**: radar de dos jugadores, alternando ofensivo/defensivo.
- **Volumen Ofensivo**: scatter USG% vs TS% con líneas de promedio de liga que arman
  cuadrantes (estrella eficiente, alto volumen ineficiente, etc.).

### 🏆 Directivo
> "El directivo mira la consistencia competitiva e institucional a lo largo del tiempo."
- **WinRate por Temporada y Fase**: barras agrupadas (regular vs playoffs).
- **Evolución del PIR** del equipo año a año.
- **Disponibilidad**: heatmap de % de partidos jugados por jugador y temporada
  (verde = disponible, rojo = lesiones/ausencias).

---

## 4. Mensajes para cerrar (30 seg)

> "En resumen, BasketStats Analytics:
> - Centraliza datos de EuroLeague y EuroCup en una sola plataforma.
> - Tiene **control de acceso por rol**: cada usuario ve lo suyo.
> - El admin gestiona la carga con **dos modos** (incremental o recarga completa).
> - Todo corre **dockerizado**, así que se levanta con un solo comando.
>
> Cada visualización responde a una historia de usuario concreta del SRS, con sus reglas
> de negocio y criterios de aceptación."

---

## Plan B (si algo falla en vivo)

- **No carga / error de DB** → "Tenemos la base ya cargada de respaldo" y mostrá los
  dashboards directamente (saltea el paso 2).
- **El pipeline tarda/falla** → usá la carga rápida; si ya está cargado, mostrá el panel
  y explicá el flujo sin ejecutarlo.
- **Docker no levanta** → tené screenshots de respaldo de cada dashboard.

---

## Credenciales

| Usuario | Contraseña | Rol |
|---|---|---|
| `admin` | `admin` | Administrador (carga de datos + todos los dashboards) |
| `Yessica` | `entrenador` | Entrenador |
| `Emiliano` | `scout` | Scout |
| `Cinthia` | `analista` | Analista |
| `Axel` | `directivo` | Directivo |
