#!/bin/sh
if [ ! -x /usr/bin/python3 ] && command -v python3 >/dev/null 2>&1; then
    ln -s "$(command -v python3)" /usr/bin/python3
fi
if command -v apt-get >/dev/null 2>&1; then
    printf 'Acquire::Retries "0";\nAcquire::http::Timeout "5";\nAcquire::https::Timeout "5";\nAcquire::ForceIPv4 "true";\n' > /etc/apt/apt.conf.d/98-apex-terminal-network
fi
