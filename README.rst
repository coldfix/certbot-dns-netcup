certbot-dns-netcup
==================

|Version| |License| |ImageSize|

netcup_ DNS Authenticator plugin for certbot_.

This plugin automates the process of completing a ``dns-01`` challenge by
creating, and subsequently removing, ``TXT`` records using the netcup `CCP
API`_ via nc_dnsapi_.

**Note:** This plugin requires certbot ≥ v2.7.

If you need support for older certbot versions, check version 1.4.X and below.

.. _netcup: https://www.netcup.de/
.. _certbot: https://certbot.eff.org/
.. _CCP API: https://www.netcup-wiki.de/wiki/CCP_API
.. _nc_dnsapi: https://github.com/nbuchwitz/nc_dnsapi
.. _certbot-dns-cloudflare: https://certbot-dns-cloudflare.readthedocs.io/en/latest/


Installation
------------

Since this package acts as a plugin for certbot_, the installation method can
vary depending on how certbot is installed.

pip
~~~

If certbot is installed normally as a python package, the plugin can be
installed using::

    pip install certbot-dns-netcup

snap
~~~~

If certbot is installed as a snap, you'll have to install this plugin as
follows::

    sudo snap install certbot-dns-netcup

Furthermore, the following seems to be required in order to connect the plugin
to certbot::

    sudo snap set certbot trust-plugin-with-root=ok
    sudo snap connect certbot:plugin certbot-dns-netcup

docker
~~~~~~

Using docker, you can pull an image that contains both certbot and a matching
version of the plugin::

    docker pull coldfix/certbot-dns-netcup


Usage
-----

To acquire a single certificate for both ``example.com`` and
``*.example.com``, waiting 1200 seconds (20min) for DNS propagation::

    certbot certonly \\
      --authenticator dns-netcup \\
      --dns-netcup-credentials ~/.secrets/certbot/netcup.ini \\
      --dns-netcup-propagation-seconds 1200 \\
      --keep-until-expiring --non-interactive --expand \
      --server https://acme-v02.api.letsencrypt.org/directory \
      -d 'example.com' \\
      -d '*.example.com'

The parameters and the format of the credentials file are described below.


Named Arguments
---------------

To start using DNS authentication for netcup, pass the following arguments on
certbot's command line:

======================================== =======================
``--authenticator dns-netcup``           select the authenticator
                                         plugin (Required)

``--dns-netcup-credentials FILE``        netcup credentials_
                                         INI file. (Required)

``--dns-netcup-propagation-seconds NUM`` | waiting time for DNS to propagate before asking
                                         | the ACME server to verify the DNS record.
                                         | (Default: 900, Recommended: >= 600)

``--dns-netcup-login-retries NUM``       | Number of login retry attempts in case the
                                         | netcup API client session times out.
                                         | (Default: 3, Recommended: >= 1)
======================================== =======================

**NOTE:**
You may need to set an unexpectedly high propagation time (≥ 900 seconds) to
give the netcup DNS time to propagate the entries! This may be annoying when
calling certbot manually but should not be a problem in automated setups.
In exceptional cases, 20 minutes may be required. See `#28`_.

.. _#28: https://github.com/coldfix/certbot-dns-netcup/issues/28


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


Docker
------

You can pull the latest version of the docker image directly from Docker Hub
as follows::

    docker pull coldfix/certbot-dns-netcup

Alternatively, the docker image can be built from a local checkout and the
included ``Dockerfile`` as follows::

    docker build -t coldfix/certbot-dns-netcup .

Once that's finished, the application can be run as follows::

    docker run --rm \
      -v /var/lib/letsencrypt:/var/lib/letsencrypt \
      -v /etc/letsencrypt:/etc/letsencrypt \
      --cap-drop=all \
      coldfix/certbot-dns-netcup certbot certonly \
        --authenticator dns-netcup \
        --dns-netcup-propagation-seconds 900 \
        --dns-netcup-credentials /var/lib/letsencrypt/netcup_credentials.ini \
        --keep-until-expiring --non-interactive --expand \
        --server https://acme-v02.api.letsencrypt.org/directory \
        --agree-tos --email "webmaster@example.com" \
        -d example.com -d '*.example.com'

You may want to change the volumes ``/var/lib/letsencrypt`` and
``/etc/letsencrypt`` to local directories where the certificates and
configuration should be stored.


.. Badges:

.. |Version| image::   https://img.shields.io/pypi/v/certbot-dns-netcup.svg
   :target:            https://pypi.python.org/pypi/certbot-dns-netcup
   :alt:               Version

.. |License| image::   https://img.shields.io/pypi/l/certbot-dns-netcup.svg
   :target:            https://github.com/coldfix/certbot-dns-netcup/blob/master/LICENSE.txt
   :alt:               License: Apache

.. |ImageSize| image:: https://img.shields.io/docker/image-size/coldfix/certbot-dns-netcup
   :target:            https://hub.docker.com/repository/docker/coldfix/certbot-dns-netcup
   :alt:               Docker image size
