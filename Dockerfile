FROM python:3.11-slim

WORKDIR /sweng26_group20-adguardanomalydetection

#Install dependencies required
COPY requirements-prod.txt .
RUN pip install --no-cache-dir --upgrade "pip>=26.0.0" && \
	pip install --no-cache-dir -r requirements-prod.txt

#Copy source
COPY . .

CMD ["python", "-m", "app.main"]

