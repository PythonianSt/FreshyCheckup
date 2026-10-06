FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
COPY templates ./templates
COPY static ./static
CMD ["sh","-c","exec gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 2 --timeout 60 app:app"]
