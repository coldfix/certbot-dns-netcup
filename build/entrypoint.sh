#!/bin/sh
CREDENTIALS=/netcup_credentials.ini
echo dns_netcup_customer_id = $DNS_NETCUP_CUSTOMER_ID > $CREDENTIALS
echo dns_netcup_api_key = $DNS_NETCUP_API_KEY >> $CREDENTIALS
echo dns_netcup_api_password = $DNS_NETCUP_API_PASSWORD >> $CREDENTIALS

certbot certonly \
    --authenticator dns-netcup \
    --dns-netcup-propagation-seconds $NETCUP_SECONDS \
    --dns-netcup-credentials $CREDENTIALS \
    --keep-until-expiring --non-interactive --expand \
    --server https://acme-v02.api.letsencrypt.org/directory \
    --agree-tos --email $EMAIL \
    $DOMAIN \
    $EXTRA_ARGS
