FROM iron/python:2

RUN apk update && apk upgrade

RUN apk add curl
RUN apk add python 
RUN apk add python-dev
RUN apk add libstdc++
RUN apk add build-base

RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python

RUN apk add man man-pages
RUN apk add bash bash-doc bash-completion

# fix numpy dependencies
RUN ln -s /usr/include/locale.h /usr/include/xlocale.h

# Add requirements.txt
ADD requirements.txt requirements.txt
 
# Install app requirements
RUN apk add uwsgi
RUN apk add --update uwsgi-python
RUN pip install -r requirements.txt
 
# Create app directory
ADD . /webapp
 
# Set the default directory for our environment
ENV HOME /webapp
WORKDIR /webapp
 
# Expose port 8000 for uwsgi
EXPOSE 8000

#uwsgi  --http-socket 0.0.0.0:8000 --module application:application --processes 1 --threads 8
ENTRYPOINT ["uwsgi", "--plugins-dir", "/usr/lib/uwsgi/", "--need-plugin",  "python", "--plugins-list", "--http", "0.0.0.0:8000", "--module", "application:application", "--processes", "1", "--threads", "8"]
