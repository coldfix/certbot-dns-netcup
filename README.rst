certbot-dns-netcup
==================

|Version| |License| |ImageSize|

netcup_ DNS Authenticator plugin for certbot_.

This plugin automates the process of completing a ``dns-01`` challenge by
creating, and subsequently removing, ``TXT`` records using the netcup `CCP
API`_ via lexicon_.

**Note:** This manual assumes certbot ≥ v1.7, which has improved the naming
scheme for external plugins. If you cannot upgrade, please also refer to the
`Old option naming scheme`_ section below.

.. _netcup: https://www.netcup.de/
.. _certbot: https://certbot.eff.org/
.. _CCP API: https://www.netcup-wiki.de/wiki/CCP_API
.. _lexicon: https://github.com/AnalogJ/lexicon
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
``*.example.com``, waiting 900 seconds for DNS propagation::

    certbot certonly \\
      --authenticator dns-netcup \\
      --dns-netcup-credentials ~/.secrets/certbot/netcup.ini \\
      --dns-netcup-propagation-seconds 900 \\
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
                                         | (Default: 10, Recommended: >= 600)
======================================== =======================

You may need to set an unexpectedly high propagation time (≥ 900 seconds) to
give the netcup DNS time to propagate the entries! This may be annoying when
calling certbot manually but should not be a problem in automated setups.


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


Old option naming scheme
------------------------

It is recommended to use the newest certbot version, at least ``v1.7``.

If you're using a certbot version below ``v1.7`` all options related to
external plugins (such as this one) must be prefixed by the name of the
plugin. This means that every occurence of ``dns-netcup`` in the command line
options must be replaced by ``certbot-dns-netcup:dns-netcup``, i.e.::

    --authenticator certbot-dns-netcup:dns-netcup
    --certbot-dns-netcup:dns-netcup-credentials
    --certbot-dns-netcup:dns-netcup-propagation-seconds

Further, every occurence of ``dns_netcup`` in the config file must be prefixed
by ``certbot_dns_netcup:``, resulting in a file like this:

.. code-block:: ini

   certbot_dns_netcup:dns_netcup_customer_id  = ...
   certbot_dns_netcup:dns_netcup_api_key      = ...
   certbot_dns_netcup:dns_netcup_api_password = ...


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
