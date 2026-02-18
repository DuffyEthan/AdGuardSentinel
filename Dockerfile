FROM python:3.11-slim

WORKDIR /sweng26_group20-adguardanomalydetection

#Install dependencies required
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

#Copy source
COPY . .

CMD ["python", "-m", "app.main"]

