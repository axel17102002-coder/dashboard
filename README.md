# 📊 Dashboard de Métricas de Básquet

Este proyecto tiene como objetivo analizar datos de competiciones de básquet (Euroleague y Eurocup) y generar distintas métricas a partir de los partidos.

---

## 📁 Estructura del proyecto

- `src/` → lógica principal (procesamiento de datos y métricas)
- `data/` → carpeta donde deben ubicarse los datasets (no incluidos en el repo)
- `app.py` → aplicación (por ejemplo, Streamlit)
- `README.md` → documentación del proyecto

---

## 📥 Datos

Los archivos `.csv` necesarios para ejecutar el proyecto **no están incluidos en el repositorio** debido a su tamaño.

👉 Descargalos desde este link:  
https://drive.google.com/drive/folders/1mEb_ba2tcMjtbECd3svlg5a23ADF7nJ4?usp=share_link

Una vez descargados, colocalos dentro de la carpeta:

```
data/
```

---

## 📈 Métricas

Las métricas implementadas en el proyecto están explicadas en detalle en el siguiente documento:

👉 https://docs.google.com/document/d/1NSKl-K3XX7cIbtfaPeltUqLuWVZzarDx_RcJlDH1w98/edit?usp=share_link

---

## 🚀 Cómo ejecutar

### Requisitos previos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado y corriendo

### Pasos

**1. Clonar el repositorio**
```bash
git clone <url-del-repo>
cd dashboard_docker
```

**2. Descargar los datos y colocarlos en `data/`**

👉 https://drive.google.com/drive/folders/1mEb_ba2tcMjtbECd3svlg5a23ADF7nJ4?usp=share_link

La carpeta `data/` debe quedar así:
```
data/
├── euroleague_box_score.csv
├── euroleague_comparison.csv
├── euroleague_header.csv
├── euroleague_play_by_play.csv
├── euroleague_players.csv
├── euroleague_points.csv
├── euroleague_teams.csv
├── eurocup_box_score.csv
├── eurocup_comparison.csv
├── eurocup_header.csv
├── eurocup_play_by_play.csv
├── eurocup_players.csv
├── eurocup_points.csv
└── eurocup_teams.csv
```

**3. Construir las imágenes (solo la primera vez)**
```bash
docker compose build
```

**4. Levantar el entorno y abrir el navegador**

En macOS podés usar el script incluido, que levanta los contenedores y abre el
dashboard automáticamente:
```bash
./start.sh
```

O hacerlo a mano:
```bash
docker compose up
```
y abrir en el navegador:
```
http://localhost:8501
```

> En Linux, dentro de `start.sh` reemplazá `open` por `xdg-open`.

Los usuarios del sistema se crean automáticamente al iniciar la app (no hace falta cargar nada para poder loguearte).

**6. Cargar los datos desde el panel de Administración**

Iniciá sesión con el usuario **admin** (ver tabla de usuarios abajo) y entrá a la
pestaña **Administración → Cargar / Actualizar datos**. Elegí el modo de carga:

- **Actualizar / Agregar (upsert)** — agrega filas nuevas y actualiza las
  existentes **sin borrar nada**. Se puede correr las veces que quieras sin
  generar duplicados. Recomendado para el día a día.
- **Recarga completa** — borra todas las tablas de estadísticas y las vuelve a
  cargar de cero.

Opciones:
- Tildá **"Carga rápida"** para omitir `play_by_play` y `comparison` (datasets muy
  pesados que el dashboard no usa). Recomendado para la mayoría de los casos.
- Apretá **"Ejecutar pipeline"**. El proceso lee los CSV de `data/`, los limpia y
  los carga en PostgreSQL.

> También podés subir/reemplazar el CSV de un dataset puntual desde la pestaña
> **"Reemplazar un dataset"**.

#### (Alternativa) Cargar los datos por terminal

```bash
# Recarga completa (borra y recarga)
docker compose run --rm web python src/cleaning/clean_master.py --modo full

# Actualizar / agregar sin borrar (upsert)
docker compose run --rm web python src/cleaning/clean_master.py --modo upsert

# Carga rápida (sin play_by_play ni comparison) — combinable con --modo
docker compose run --rm web python src/cleaning/clean_master.py --modo upsert --datasets header,box_score,players,teams,points
```

---

### Usuarios del sistema

| Usuario  | Contraseña   | Rol        |
|----------|--------------|------------|
| admin    | admin        | admin      |
| Yessica  | entrenador   | entrenador |
| Emiliano | scout        | scout      |
| Cinthia  | analista     | analista   |
| Axel     | directivo    | directivo  |

> El rol **admin** tiene acceso al panel de carga de datos y a todos los dashboards.

---

### Ejecuciones posteriores

Una vez que los datos están cargados en la base de datos, para volver a usar el dashboard solo necesitás:

```bash
docker compose up
```

Y abrir `http://localhost:8501`. No es necesario volver a correr el pipeline ni el build.

---

## 🧠 Notas

- Los datos son pesados, por eso no se incluyen en el repo.
- La base de datos se almacena en un volumen Docker local (`postgres_data`). Si eliminás el volumen con `docker compose down -v`, tenés que volver a cargar los datos desde el paso 4.
- Si ya tenés los datos cargados y solo modificaste código, podés saltar el DROP de tablas con:
  ```bash
  docker compose run --rm web python src/cleaning/clean_master.py --skip-drop
  ```
