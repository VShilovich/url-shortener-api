FROM python:3.10-slim

RUN mkdir /fastapi_app
WORKDIR /fastapi_app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# даем права на выполнение скрипта запуска
RUN chmod a+x docker/*.sh
CMD ["/fastapi_app/docker/app.sh"]