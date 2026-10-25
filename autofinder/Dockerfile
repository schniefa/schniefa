FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
COPY static ./static
ENV AUTOFINDER_CONFIG=/config/config.json AUTOFINDER_DATA=/data
EXPOSE 8080
CMD ["python", "app.py"]
