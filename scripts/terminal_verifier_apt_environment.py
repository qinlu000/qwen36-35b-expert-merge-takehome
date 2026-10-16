"""Apply native package transport configuration explicitly in the verifier phase."""
from terminal_verifier_environment import TerminalVerifierEnvironment

APT_SETUP=r'''mkdir -p /etc/apt/apt.conf.d
if command -v apt-get >/dev/null 2>&1; then
printf 'APT::Sandbox::User "root";\nAcquire::Retries "0";\nAcquire::http::Timeout "15";\nAcquire::https::Timeout "15";\nAcquire::ForceIPv4 "true";\n' > /etc/apt/apt.conf.d/98-apex-native
for f in /etc/apt/sources.list /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources; do
 [ -f "$f" ] || continue
 sed -i 's|http://deb.debian.org/debian|https://mirrors.tuna.tsinghua.edu.cn/debian|g;s|http://security.debian.org/debian-security|https://mirrors.tuna.tsinghua.edu.cn/debian-security|g;s|http://archive.ubuntu.com/ubuntu|https://mirrors.tuna.tsinghua.edu.cn/ubuntu|g;s|http://security.ubuntu.com/ubuntu|https://mirrors.tuna.tsinghua.edu.cn/ubuntu|g' "$f"
done
fi'''


class TerminalVerifierAptEnvironment(TerminalVerifierEnvironment):
    async def _prepare_verifier(self):
        await super()._prepare_verifier()
        result=await super().exec(APT_SETUP,timeout_sec=20)
        if result.return_code:raise RuntimeError('Verifier package transport setup failed')
