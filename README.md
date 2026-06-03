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

**4. Levantar la base de datos**
```bash
docker compose up -d db
```

**5. Cargar los datos (tarda ~1 hora la primera vez)**

Este paso corre el pipeline de limpieza e ingesta: lee los CSVs de `data/`, los procesa y los carga en la base de datos PostgreSQL.

```bash
docker compose run --rm web python src/cleaning/clean_master.py
```

**6. Levantar el dashboard**
```bash
docker compose up
```

**7. Abrir en el navegador**
```
http://localhost:8501
```

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
