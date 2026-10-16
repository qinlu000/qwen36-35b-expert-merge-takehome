#!/bin/sh
# Cached server venv is read-only. Supply the link before the shared root-map
# hook, so it need not create a replacement server venv on Python base images.
if [ ! -x /usr/bin/python3 ] && command -v python3 >/dev/null 2>&1; then
    ln -s "$(command -v python3)" /usr/bin/python3
fi
