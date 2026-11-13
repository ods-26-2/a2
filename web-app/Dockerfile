# ==============================================================================
# Multi-stage Dockerfile para web-app (React Vite frontend + FastAPI backend)
# ==============================================================================

# ------------------------------------------------------------------------------
# Estágio 1: Build do Frontend (Node.js)
# ------------------------------------------------------------------------------
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

# Instalação de dependências aproveitando cache de camadas
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Cópia do código-fonte do frontend e compilação do bundle estático (dist)
COPY frontend/ ./
RUN npm run build

# ------------------------------------------------------------------------------
# Estágio 2: Imagem Final de Execução (Python)
# ------------------------------------------------------------------------------
FROM python:3.12-slim AS runner
WORKDIR /app

# Variáveis de ambiente para execução em produção
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    HOST=0.0.0.0

# Utilitários de sistema (curl para verificação de saúde)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instalação das dependências Python
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Cópia do backend e do entrypoint da aplicação
COPY backend/ ./backend/
COPY main.py ./

# Cópia dos arquivos estáticos compilados do frontend (Vite dist)
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Cria diretório para persistência do banco SQLite
RUN mkdir -p /app/backend/db

# Porta padrão de exposição
EXPOSE 8080

# Healthcheck do container
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/admin || exit 1

# Inicialização da aplicação
CMD ["python", "main.py"]
