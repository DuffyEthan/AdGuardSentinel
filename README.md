# Setup

## Linux

### Timescale and PostgresSQL setup
[See https://www.tigerdata.com/docs/self-hosted/latest/install/installation-linux#install-timescale_db-on-linux for other Linux Distro]

```
Apt:
# apt install gnupg postgresql-common apt-transport-https lsb-release wget
# /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh
# echo "deb https://packagecloud.io/timescale/timescaledb/debian/ $(lsb_release -c -s) main" | sudo tee /etc/apt/sources.list.d/timescaledb.list
# wget -O - https://packagecloud.io/timescale/timescaledb/gpgkey | sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/timescaledb.gpg
# apt update
# apt install timescaledb-2-postgresql-18 postgresql-client-18
# systemctl restart postgresql
```

### Add user to use Postgres

```
# su postgres
$ createuser -d [insert_your_username]
```

### Create First DB

```
$ createdb [insert_db_name]
```

### Access DB

```
$ psql [insert_db_name]
```

put the following to use timescaleDB

```
CREATE EXTENSION IF NOT EXISTS timescaledb;
```

### Psycopg3 setup
```
# apt install python3 python3-psycopg
```