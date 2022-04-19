ARG FROM=certbot/certbot
FROM ${FROM}

COPY . src/certbot-dns-netcup

RUN pip install --no-cache-dir --editable src/certbot-dns-netcup

ENTRYPOINT ["/usr/bin/env"]
