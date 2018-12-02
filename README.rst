certbot-dns-netcup
==================

netcup_ DNS Authenticator plugin for certbot_.

This plugin automates the process of completing a ``dns-01`` challenge by
creating, and subsequently removing, TXT records using the netcup `CCP API`_
via nc_dnsapi_.

Forked from certbot-dns-cloudflare_.

.. _netcup: https://www.netcup.de/
.. _certbot: https://certbot.eff.org/
.. _CCP API: https://www.netcup-wiki.de/wiki/CCP_API
.. _nc_dnsapi: https://github.com/nbuchwitz/nc_dnsapi
.. _certbot-dns-cloudflare: https://certbot-dns-cloudflare.readthedocs.io/en/latest/


Named Arguments
---------------

=======================================================  =====================================
``--certbot-dns-netcup:dns-netcup-credentials``          netcup credentials_ INI file.
                                                         (Required)
``--certbot-dns-netcup:dns-netcup-propagation-seconds``  The number of seconds to wait for DNS
                                                         to propagate before asking the ACME
                                                         server to verify the DNS record.
                                                         (Default: 10)
=======================================================  =====================================

Note that the seemingly redundant ``certbot-dns-netcup:`` prefix is imposed by
certbot for external plugins.

You may need to set a relatively high propagation time (>= 10 minutes) to give
the netcup DNS time to propagate the entries! This should not be a problem in
automated setups.


Credentials
-----------

Use of this plugin requires a configuration file containing netcup API
credentials, obtained from your netcup
`account page <https://ccp.netcup.net/run/daten_aendern.php?sprung=api>`_.
See also the `CCP API`_ documentation.

An example ``credentials.ini`` file:

.. code-block:: ini

   certbot_dns_netcup:dns_netcup_customer_id  = 123456
   certbot_dns_netcup:dns_netcup_api_key      = 0123456789abcdef0123456789abcdef01234567
   certbot_dns_netcup:dns_netcup_api_password = abcdef0123456789abcdef01234567abcdef0123
   certbot_dns_netcup:dns_netcup_timeout      = 60

The path to this file can be provided interactively or using the
``--certbot-dns-netcup:dns-netcup-credentials`` command-line argument. Certbot
records the path to this file for use during renewal, but does not store the
file's contents.

The ``timeout`` entry can be used to avoid timeouts due to slow response times
of the netcup API servers. If this entry is not given it defaults to 60 seconds.

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


Examples
--------

To acquire a single certificate for both ``example.com`` and
``www.example.com``, waiting 900 seconds for DNS propagation:

.. code-block:: bash

   certbot certonly \\
     --authenticator certbot-dns-netcup:dns-netcup \\
     --certbot-dns-netcup:dns-netcup-credentials ~/.secrets/certbot/netcup.ini \\
     --certbot-dns-netcup:dns-netcup-propagation-seconds 900 \\
     -d example.com \\
     -d www.example.com
