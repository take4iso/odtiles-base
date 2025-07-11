FROM oraclelinux:8

# サーバー名
ARG SERVER_NAME=localhost
# uwsgi のワーカー数
ARG UWSGI_WORKERS=8
# uwsgi のポート番号
ARG UWSGI_PORT=0.0.0.0:8080
# タイルソースフォルダ
ARG TILE_SOURCE_FOLDER=/mnt/odtiles/tilesrc/
# タイル出力フォルダ
ARG TILE_OUTPUT_FOLDER=/mnt/odtiles/tileout/
# タイルの最大キャッシュ期間（秒）
ARG TILE_MAX_AGE=86400
# タイルの最大キャッシュ期間（ライブタイル用、秒）
ARG TILE_MAX_AGE_LIVE=60



RUN dnf config-manager --enable ol8_codeready_builder && \
    dnf update && \
    dnf -y install https://dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm && \
    dnf -y install langpacks-ja glibc-langpack-ja.x86_64 wget gcc gcc-c++ make cmake git m4 libcurl-devel python312 python3.12-devel python3.12-pip unzip libdap zlib-devel proj proj-devel swig

RUN alternatives --set python3 /usr/bin/python3.12
RUN pip3 install --upgrade pip && \
    pip3 install setuptools numpy

# sqlite3のインストール
RUN cd /root && \
    wget https://sqlite.org/2025/sqlite-autoconf-3490100.tar.gz && \
    tar -zxvf sqlite-autoconf-3490100.tar.gz && \
    cd sqlite-autoconf-3490100 && \
    ./configure --prefix=/usr --enable-all && \
    CFLAGS="-DHAVE_READLINE=1 -DSQLITE_ALLOW_URI_AUTHORITY=1 -DSQLITE_ENABLE_COLUMN_METADATA=1 -DSQLITE_ENABLE_DBPAGE_VTAB=1 -DSQLITE_ENABLE_DBSTAT_VTAB=1 -DSQLITE_ENABLE_DESERIALIZE=1 -DSQLITE_ENABLE_FTS4=1 -DSQLITE_ENABLE_FTS5=1 -DSQLITE_ENABLE_GEOPOLY=1 -DSQLITE_ENABLE_JSON1=1 -DSQLITE_ENABLE_MEMSYS3=1 -DSQLITE_ENABLE_PREUPDATE_HOOK=1 -DSQLITE_ENABLE_RTREE=1 -DSQLITE_ENABLE_SESSION=1 -DSQLITE_ENABLE_SNAPSHOT=1 -DSQLITE_ENABLE_STMTVTAB=1 -DSQLITE_ENABLE_UPDATE_DELETE_LIMIT=1 -DSQLITE_ENABLE_UNLOCK_NOTIFY=1 -DSQLITE_INTROSPECTION_PRAGMAS=1 -DSQLITE_USE_ALLOCA=1 -DSQLITE_USE_FCNTL_TRACE=1 -DSQLITE_HAVE_ZLIB=1" && \ 
    make && \
    make install

# hdf5のインストール（バージョン注意：1.14.6だとnetcdfのビルドでエラーが出る）
RUN cd /root && \
    wget https://github.com/HDFGroup/hdf5/releases/download/hdf5_1.14.5/hdf5.tar.gz && \
    tar -zxvf hdf5.tar.gz && \
    cd hdf5-1.14.5 && \
    mkdir build && \
    cd build && \
    cmake -G "Unix Makefiles" -DCMAKE_BUILD_TYPE:STRING=Release -DBUILD_SHARED_LIBS:BOOL=ON -DBUILD_TESTING:BOOL=ON -DHDF5_BUILD_TOOLS:BOOL=ON -DCMAKE_INSTALL_PREFIX=/usr -DHDF5_BUILD_CPP_LIB:BOOL=ON ../ && \
    make && \
    #ctest . -C Release && \
    make install

# netcdfのインストール
RUN cd /root && \
    git clone https://github.com/Unidata/netcdf-c.git -b v4.9.3 && \
    cd netcdf-c && \
    mkdir build && \
    cd build && \
    cmake -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_PREFIX_PATH=/usr -DNETCDF_ENABLE_HDF5=ON ../ && \
    make && \
    #ctest && \
    make install


# gdalのインストール
RUN cd /root && \
    git clone https://github.com/OSGeo/gdal.git -b v3.11.1 && \
    cd gdal && \
    mkdir build && \
    cd build && \
    cmake -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_BUILD_TYPE=Release -DBUILD_PYTHON_BINDINGS:BOOL=ON .. && \
    cmake --build . && \
    cmake --build . --target install

RUN pip3 install django uwsgi wget requests

# gdal2tiles(ondemand pache) のインストール
RUN cd /root && \
    git clone https://github.com/take4iso/gdal2tiles && \
    cd gdal2tiles && \
    python3 setup.py install

# odtilesのインストール
COPY odtiles/ /opt/odtiles/

RUN sed -i "s!ALLOWED_HOSTS = ['localhost']!ALLOWED_HOSTS = ['${SERVER_NAME}']!" /opt/odtiles/odtiles/settings.py
RUN sed -i "s!CSRF_TRUSTED_ORIGINS = ['http://locslhost']!CSRF_TRUSTED_ORIGINS = ['http://${SERVER_NAME}','https://${SERVER_NAME}']!" /opt/odtiles/odtiles/settings.py
RUN sed -i "s!workers = 8!workers = ${UWSGI_WORKERS}!" /opt/odtiles/odtiles/uwsgi.ini
RUN sed -i "s!0.0.0.0:8080!${UWSGI_PORT}!" /opt/odtiles/odtiles/uwsgi.ini
RUN sed -i "s!TILE_SOURCE_FOLDER = '/mnt/odtiles/tilesrc'!TILE_SOURCE_FOLDER = '${TILE_SOURCE_FOLDER}'!" /opt/odtiles/odtiles/settings.py
RUN sed -i "s!TILE_OUTPUT_FOLDER = '/mnt/odtiles/tileout'!TILE_OUTPUT_FOLDER = '${TILE_OUTPUT_FOLDER}'!" /opt/odtiles/odtiles/settings.py
RUN sed -i "s!TILE_MAX_AGE = 86400!TILE_MAX_AGE = ${TILE_MAX_AGE}!" /opt/odtiles/odtiles/settings.py
RUN sed -i "s!TILE_MAX_AGE_LIVE = 60!TILE_MAX_AGE_LIVE = ${TILE_MAX_AGE_LIVE}!" /opt/odtiles/odtiles/settings.py


RUN chmod +x /opt/odtiles/start.sh

# あとかたづけ
RUN rm -rf /root/*

CMD ["/opt/odtiles/start.sh"]
#CMD ["/usr/sbin/init"]
