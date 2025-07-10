#!/bin/bash

# DockerコンテナのENTRYPOINT
export LD_LIBRARY_PATH=/usr/lib

# UWSGIの起動
uwsgi --ini /opt/odtiles/odtiles/uwsgi.ini 
