FROM tiangolo/meinheld-gunicorn-flask:python3.9
MAINTAINER g.golyshev@gmail.com
RUN apt-get update
RUN apt -y install ffmpeg
#RUN apt-get -y install vim nano

WORKDIR ..

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt
COPY ./app /app
ENV REDIS="redis://:@172.17.0.2"
#RUN printenv

#ENTRYPOINT /bin/sh
ENTRYPOINT  gunicorn --conf gunicorn_conf.py --bind 0.0.0.0:5052 main:app

