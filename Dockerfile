FROM python:3.8-slim-buster

# System deps
RUN apt update && apt upgrade -y && \
    apt install -y git && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt /requirements.txt

# Install Python deps
RUN pip3 install --no-cache-dir -U pip setuptools wheel && \
    pip3 install --no-cache-dir -U -r /requirements.txt

WORKDIR /app
COPY . .

CMD ["python", "bot.py"]
