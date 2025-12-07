#!/bin/sh
set -e

python manage.py migrate --noinput

if [ "$COLLECT_STATIC" = "1" ] || [ "$DJANGO_COLLECTSTATIC" = "1" ]; then
    python manage.py collectstatic --noinput
fi

exec "$@"
