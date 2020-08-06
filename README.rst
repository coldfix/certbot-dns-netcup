certbot-dns-netcup
==================

netcup_ DNS Authenticator plugin for certbot_.

This plugin automates the process of completing a ``dns-01`` challenge by
creating, and subsequently removing, TXT records using the netcup `CCP API`_
via lexicon_.

.. _netcup: https://www.netcup.de/
.. _certbot: https://certbot.eff.org/
.. _CCP API: https://www.netcup-wiki.de/wiki/CCP_API
.. _lexicon: https://github.com/AnalogJ/lexicon
.. _certbot-dns-cloudflare: https://certbot-dns-cloudflare.readthedocs.io/en/latest/


Installation
------------

::

    pip install certbot-dns-netcup


Named Arguments
---------------

To start using DNS authentication for netcup, pass the following arguments on
certbot's command line:

======================================== =======================
``--authenticator dns-netcup``           select the authenticator
                                         plugin (Required)

``--dns-netcup-credentials FILE``        netcup credentials_
                                         INI file. (Required)

``--dns-netcup-propagation-seconds 900`` | waiting time for DNS to propagate before asking
                                         | the ACME server to verify the DNS record.
                                         | (Default: 10, Recommended: >= 600)
======================================== =======================

You may need to set an even higher propagation time (>= 900 seconds) to give
the netcup DNS time to propagate the entries! This may be annoying when
calling certbot manually but should not be a problem in automated setups.

**Note:** If you're using a certbot version below ``v1.7``, each occurence of
``dns-netcup`` above must be prefixed by the string ``certbot-dns-netcup:``,
i.e.: ``--authenticator certbot-dns-netcup:dns-netcup``,
``--certbot-dns-netcup:dns-netcup-credentials``, and
``--certbot-dns-netcup:dns-netcup-propagation-seconds``. It is recommended to
upgrade certbot to the newest version.


Credentials
-----------

Use of this plugin requires a configuration file containing netcup API
credentials, obtained from your netcup `account page`_. See also the `CCP
API`_ documentation.

.. _account page: https://ccp.netcup.net/run/daten_aendern.php?sprung=api

An example ``credentials.ini`` file:

.. code-block:: ini

   dns_netcup_customer_id  = 123456
   dns_netcup_api_key      = 0123456789abcdef0123456789abcdef01234567
   dns_netcup_api_password = abcdef0123456789abcdef01234567abcdef0123

The path to this file can be provided interactively or using the
``--dns-netcup-credentials`` command-line argument. Certbot
records the path to this file for use during renewal, but does not store the
file's contents.

**CAUTION:** You should protect these API credentials as you would the
password to your netcup account. Users who can read this file can use these
credentials to issue arbitrary API calls on your behalf. Users who can cause
Certbot to run using these credentials can complete a ``dns-01`` challenge to
acquire new certificates or revoke existing certificates for associated
domains, even if those domains aren't being managed by this server.

Certbot will emit a warning if it detects that the credentials file can be
accessed by other users on your system. The warning reads "Unsafe permissions
on credentials configuration file", followed by the path to the credentials
file. This warning will be emitted each time Certbot uses the credentials file,
including for renewal, and cannot be silenced except by addressing the issue
(e.g., by using a command like ``chmod 600`` to restrict access to the file).

**Note:** For certbot versions below ``v1.7``, each occurence of
``dns_netcup`` above must be prefixed by the string ``certbot_dns_netcup:``,
i.e.:

.. code-block:: ini

   certbot_dns_netcup:dns_netcup_customer_id  = ...
   certbot_dns_netcup:dns_netcup_api_key      = ...
   certbot_dns_netcup:dns_netcup_api_password = ...


Examples
--------

To acquire a single certificate for both ``example.com`` and
``*.example.com``, waiting 900 seconds for DNS propagation:

.. code-block:: bash

    certbot certonly \\
      --authenticator dns-netcup \\
      --dns-netcup-credentials ~/.secrets/certbot/netcup.ini \\
      --dns-netcup-propagation-seconds 900 \\
      --no-self-upgrade \
      --keep-until-expiring --non-interactive --expand \
      --server https://acme-v02.api.letsencrypt.org/directory \
      -d 'example.com' \\
      -d '*.example.com'


Docker
------

You can build a docker image from source using the included ``Dockerfile``
or pull the latest version directly from Docker Hub::

    docker pull coldfix/certbot-dns-netcup

Once that's finished, the application can be run as follows::

    docker run --rm \
      -v /var/lib/letsencrypt:/var/lib/letsencrypt \
      -v /etc/letsencrypt:/etc/letsencrypt \
      --cap-drop=all \
      coldfix/certbot-dns-netcup certbot certonly \
        --authenticator dns-netcup \
        --dns-netcup-propagation-seconds 900 \
        --dns-netcup-credentials /var/lib/letsencrypt/netcup_credentials.ini \
        --no-self-upgrade \
        --keep-until-expiring --non-interactive --expand \
        --server https://acme-v02.api.letsencrypt.org/directory \
        -d example.com -d '*.example.com'

You may want to change the volumes ``/var/lib/letsencrypt`` and
``/etc/letsencrypt`` to local directories where the certificates and
configuration should be stored.

**Note:** For some (older?) versions of certbot, the docker image runs
``certbot`` from its entrypoint, which means that you may have to remove the
executable name ``certbot`` from the above command.
