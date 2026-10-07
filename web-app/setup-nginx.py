#!/usr/bin/env python3
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def run(*cmd):
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        sys.exit(f"Falha em {' '.join(cmd)}:\n{exc.stderr or exc.stdout}")


def server_conf(domain):
    name = f"{domain} www.{domain}" if domain else "_"
    return f"""# Reverse proxy: nginx na porta 80 -> app FastAPI na 8080
server {{
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name {name};

    location / {{
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_read_timeout 60s;
        proxy_connect_timeout 5s;
    }}
}}
"""


def main():
    if os.geteuid() != 0:
        os.execvp("sudo", ["sudo", sys.executable, str(Path(__file__).resolve())] + sys.argv[1:])

    os_release = {}
    for line in Path("/etc/os-release").read_text().splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            os_release[key] = value.strip('"')
    distro = os_release.get("ID", "")

    if distro in ("ubuntu", "debian"):
        conf = Path("/etc/nginx/sites-available/a2.conf")
        linked = Path("/etc/nginx/sites-enabled/a2.conf")
    elif distro == "fedora":
        conf = Path("/etc/nginx/conf.d/a2.conf")
        linked = None
    else:
        sys.exit(f"Distro não suportada: {distro or 'desconhecida'}.")

    domain = input("Domínio para HTTPS (Enter para pular): ").strip().lower()
    if domain and not re.fullmatch(r"[a-z0-9.-]+", domain):
        sys.exit("Domínio inválido.")

    conf.write_text(server_conf(domain or None))

    if linked is not None:
        linked.unlink(missing_ok=True)
        os.symlink(conf, linked)
        Path("/etc/nginx/sites-enabled/default").unlink(missing_ok=True)

    run("nginx", "-t")
    run("systemctl", "enable", "--now", "nginx")
    run("systemctl", "reload", "nginx")

    if domain:
        if not shutil.which("certbot"):
            sys.exit("certbot não encontrado — instale-o (ex.: apt install certbot python3-certbot-nginx).")
        run("certbot", "--nginx", "-d", domain, "-d", f"www.{domain}", "--redirect",
            "--non-interactive", "--agree-tos", "--register-unsafely-without-email")
        run("systemctl", "enable", "--now", "certbot.timer")

    print(f"nginx configurado: 80 -> 8080" + (f", HTTPS em https://{domain}" if domain else ""))


if __name__ == "__main__":
    main()