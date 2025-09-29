FROM python:3.11-slim

WORKDIR /app

COPY unified_simulator.py /app/unified_simulator.py
COPY datasets/ /app/datasets/
COPY requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

ENV BROKER_HOST=emqx
ENV BROKER_PORT=1883
ENV PYTHONUNBUFFERED=1

CMD ["python", "unified_simulator.py", "--legacy", "--broker", "emqx", "--port", "1883"]
