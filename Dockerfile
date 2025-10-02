FROM python:3.12-slim

WORKDIR /app

COPY canonical_simulator.py /app/canonical_simulator.py
COPY canonical_dataset.csv /app/canonical_dataset.csv
COPY requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

ENV BROKER_HOST=emqx
ENV BROKER_PORT=1883
ENV PYTHONUNBUFFERED=1

CMD ["python", "canonical_simulator.py", "--broker", "emqx", "--port", "1883", "--duration", "0"]
