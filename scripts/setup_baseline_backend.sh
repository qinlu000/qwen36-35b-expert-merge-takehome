#!/usr/bin/env bash
# Unprivileged, project-local tools for the accepted Ubuntu22 host backend.
set -euo pipefail
task_root="$(cd "$(dirname "$0")/.." && pwd)"
tool_root="$task_root/artifacts/tools/slirp4netns"
mkdir -p "$tool_root/debs" "$tool_root/rootfs"
cd "$tool_root/debs"
if [ ! -f slirp4netns_1.0.1-2_amd64.deb ] || [ ! -f libslirp0_4.6.1-1ubuntu0.2_amd64.deb ]; then
    apt-get download slirp4netns=1.0.1-2 libslirp0=4.6.1-1ubuntu0.2
fi
sha256sum --check <<'CHECKSUMS'
2bcc232b44309d9aa21f84764e813059f9b12902aee81419e8d3adb7f740dc41  slirp4netns_1.0.1-2_amd64.deb
b313de55b17cf8974996706b9cc70e4de387a39decf0bc3fa3a4256734476ee8  libslirp0_4.6.1-1ubuntu0.2_amd64.deb
CHECKSUMS
for package in ./*.deb; do
    dpkg-deb --extract "$package" "$tool_root/rootfs"
done
LD_LIBRARY_PATH="$tool_root/rootfs/usr/lib/x86_64-linux-gnu" \
    "$tool_root/rootfs/usr/bin/slirp4netns" --version
