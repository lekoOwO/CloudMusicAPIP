FROM python:3-alpine

EXPOSE 5000
COPY . /cm
WORKDIR /cm
RUN apk add --no-cache --virtual .build-deps gcc musl-dev \
    && pip install -r requirements.txt \
    && apk del .build-deps gcc musl-dev
CMD python index.py