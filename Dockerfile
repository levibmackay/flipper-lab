FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y iputils-ping && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server/ ./server/

RUN echo "FLAG{bad_usb_wins}" > /app/server/flag.txt

EXPOSE 5000

CMD ["python3", "server/app.py"]
