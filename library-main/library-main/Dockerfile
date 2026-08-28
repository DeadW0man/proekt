FROM python:3.13-slim

# Не пишем .pyc в контейнер, логи видим сразу
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Сначала зависимости — слой кэшируется, пока не менялся requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Затем код приложения
COPY . .

# Запускаемся не под root. /app/data — каталог для БД (том из docker-compose)
RUN useradd -m appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 5000

# Точка входа: python -m app.main (важно: именно -m, чтобы работали импорты api/db/...)
CMD ["python", "-m", "app.main"]
