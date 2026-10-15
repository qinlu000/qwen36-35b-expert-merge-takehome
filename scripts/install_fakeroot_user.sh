#!/usr/bin/env bash
# Debian bullseye binaries, extracted only into this project's tools directory.
set -euo pipefail
task_root="${1:-$(pwd)}"
dest="$task_root/artifacts/tools/fakeroot-1.25.3"
mkdir -p "$dest/rootfs"

for package in fakeroot libfakeroot; do
    case "$package" in
        fakeroot) checksum=b67966ee7bad5e87f4ae7eecb6f4fe76ba7c12af7b9876c09f1e758eb742232c ;;
        libfakeroot) checksum=04dace71ea2e14940bd0491e41331df77b5a5da82fe98ead228df756b4fe0bc8 ;;
    esac
    archive="$dest/${package}_1.25.3-1.1_amd64.deb"
    if [ ! -f "$archive" ]; then
        curl -fL --retry 2 -o "$archive" "https://deb.debian.org/debian/pool/main/f/fakeroot/${package}_1.25.3-1.1_amd64.deb"
    fi
    printf '%s  %s\n' "$checksum" "$archive" | sha256sum -c -
    ar p "$archive" data.tar.xz | tar -xJ -C "$dest/rootfs"
done

# Same relocation principle as Apptainer's official install-unprivileged.sh.
sed -i \
    -e 's|^FAKEROOT_PREFIX=/usr$|FAKEROOT_BINDIR=$(dirname "$(readlink -f "$0")")|' \
    -e 's|^FAKEROOT_BINDIR=/usr/bin$|FAKEROOT_PREFIX=${FAKEROOT_BINDIR%/*}|' \
    -e 's|^PATHS=/usr/lib.*$|PATHS=${FAKEROOT_PREFIX}/lib/x86_64-linux-gnu/libfakeroot|' \
    "$dest/rootfs/usr/bin/fakeroot-sysv"
ln -sfn fakeroot-sysv "$dest/rootfs/usr/bin/fakeroot"
ln -sfn faked-sysv "$dest/rootfs/usr/bin/faked"
"$dest/rootfs/usr/bin/fakeroot" --version
