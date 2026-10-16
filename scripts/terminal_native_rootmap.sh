#!/bin/sh
if command -v apt-get >/dev/null 2>&1; then
 printf 'APT::Sandbox::User "root";\nAcquire::Retries "0";\nAcquire::http::Timeout "15";\nAcquire::https::Timeout "15";\nAcquire::ForceIPv4 "true";\n' > /etc/apt/apt.conf.d/98-apex-native
 for f in /etc/apt/sources.list /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources; do
  [ -f "$f" ] || continue
  sed -i 's|http://deb.debian.org/debian|https://mirrors.tuna.tsinghua.edu.cn/debian|g;s|http://security.debian.org/debian-security|https://mirrors.tuna.tsinghua.edu.cn/debian-security|g;s|http://archive.ubuntu.com/ubuntu|https://mirrors.tuna.tsinghua.edu.cn/ubuntu|g;s|http://security.ubuntu.com/ubuntu|https://mirrors.tuna.tsinghua.edu.cn/ubuntu|g' "$f"
 done
fi
