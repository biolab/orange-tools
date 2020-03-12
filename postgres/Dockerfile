FROM postgres:11

RUN  apt-get update && apt-get install -y git build-essential postgresql-server-dev-11  \
 && git clone -n https://github.com/tvondra/quantile.git  \
 && cd quantile \
 # Release 1.1.7
 && git checkout 244b6285e2c6a8d73bc555d7103200985e371bfa \
 && make install \
 && apt-get --purge autoremove -y git build-essential postgresql-server-dev-11 \
 && rm -rf /var/lib/apt/lists/*

COPY install_extensions.sql /docker-entrypoint-initdb.d
