# Use a slim Python base
FROM python:3.11-slim

# set workdir
WORKDIR /app

# copy simulator and deps
COPY simulator_9devices.py /app/simulator_9devices.py
COPY requirements.txt /app/requirements.txt

# minimize layers: install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
    && pip install --no-cache-dir -r /app/requirements.txt \
    && apt-get remove -y gcc \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# default envs (overrideable by docker-compose)
ENV BROKER_HOST=emqx
ENV BROKER_PORT=1883
ENV ENABLE_ATTACKS=false
ENV PYTHONUNBUFFERED=1

# entrypoint runs the simulator; allow override
CMD ["sh", "-c", "python /app/simulator_9devices.py --broker ${BROKER_HOST} --port ${BROKER_PORT} $( [ \"$ENABLE_ATTACKS\" = \"true\" ] && echo --enable-attacks )"]
