#!/bin/sh
# Runs inside Apptainer's writable temporary layer before Harbor bootstrap.
if [ ! -x /usr/bin/python3 ] && command -v python3 >/dev/null 2>&1; then
    existing_python=$(command -v python3)
    ln -s "$existing_python" /usr/bin/python3
    # apt may later replace /usr/bin/python3 while installing asciinema.
    "$existing_python" -m venv --copies /opt/harbor-server
fi
if command -v apt-get >/dev/null 2>&1; then
    printf 'APT::Sandbox::User "root";\n' > /etc/apt/apt.conf.d/99-apex-rootmap
fi
