# 1. Usamos una versión ligera de Python
FROM python:3.12-slim

# 2. Directorio de trabajo dentro del contenedor
WORKDIR /app

# 3. Instalar herramientas necesarias para compilar conectores de bases de datos
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 4. Copiar e instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copiar TODO el código del proyecto al contenedor
COPY . .

# 6. Exponer el puerto de Streamlit
EXPOSE 8501

# 7. Comando para arrancar Streamlit apuntando a la ruta exacta de tu app.py
CMD ["streamlit", "run", "src/dashboards/app.py", "--server.port=8501", "--server.address=0.0.0.0"]