#!/bin/bash
export LD_LIBRARY_PATH=/usr/lib


# UPLOAD_API_TOKENの設定
cd /opt/odtiles
python3 ./init_token.py
# UWSGIの起動
uwsgi --ini /opt/odtiles/odtiles/uwsgi.ini 
