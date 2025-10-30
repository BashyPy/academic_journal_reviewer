FROM python:3.11-slim

WORKDIR /app

# Create logs directory
RUN mkdir -p /app/logs

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY run.py .

EXPOSE 8000

CMD ["python", "run.py"]