FROM python:3.9-slim
WORKDIR /app
RUN pip install gunicorn==20.1.0
COPY requirements.txt .
RUN apt-get update && apt-get upgrade -y && \
    pip install --upgrade pip && pip install -r requirements.txt --no-cache-dir
COPY arial.ttf /app/static/
COPY . ./
CMD ["gunicorn", "backend.wsgi:application", "--bind", "0.0.0.0:7000"]