#!/bin/bash

docker build --build-arg APP_NAME=tone --build-arg ENV=daily -f docker/Dockerfile -t tone:$1 .
# docker build --build-arg APP_NAME=tone --build-arg ENV=daily -f docker/Dockerfile -t tone:v1.0.0 .
