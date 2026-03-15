#!/bin/bash
# init-hba.sh
echo "host replication all all trust" >> "$PGDATA/pg_hba.conf"