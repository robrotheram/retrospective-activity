FROM python:3

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV MONGO_HOST "192.168.99.100"
ENV MONGO_PORT 27017


EXPOSE 5000
CMD [ "python", "./app.py" ]

