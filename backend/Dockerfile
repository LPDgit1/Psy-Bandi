FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY certs /usr/local/share/ca-certificates/local-certs
RUN update-ca-certificates
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ENV PIP_CERT=/etc/ssl/certs/ca-certificates.crt

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN python -c "import certifi, pathlib; cert_dir = pathlib.Path('/usr/local/share/ca-certificates/local-certs'); certs = sorted(cert_dir.glob('*.crt')); bundle = pathlib.Path(certifi.where()); bundle.write_text(bundle.read_text() + ''.join('\n' + cert.read_text() for cert in certs))"

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
