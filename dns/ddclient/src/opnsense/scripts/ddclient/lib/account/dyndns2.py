"""
    Copyright (c) 2023 Ad Schellevis <ad@opnsense.org>
    All rights reserved.

    Redistribution and use in source and binary forms, with or without
    modification, are permitted provided that the following conditions are met:

    1. Redistributions of source code must retain the above copyright notice,
     this list of conditions and the following disclaimer.

    2. Redistributions in binary form must reproduce the above copyright
     notice, this list of conditions and the following disclaimer in the
     documentation and/or other materials provided with the distribution.

    THIS SOFTWARE IS PROVIDED ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES,
    INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY
    AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
    AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY,
    OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
    SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
    INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
    CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
    ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
    POSSIBILITY OF SUCH DAMAGE.
"""
import syslog
import requests
from requests.auth import HTTPBasicAuth
from . import BaseAccount


class DynDNS2(BaseAccount):
    _priority = 65535

    _services = {
        'dyndns2': 'members.dyndns.org',
        'dns-o-matic': 'updates.dnsomatic.com',
        'dynu': 'api.dynu.com',
        'he-net': 'dyn.dns.he.net',
        'he-net-tunnel': 'ipv4.tunnelbroker.net',
        'inwx': 'dyndns.inwx.com',
        'loopia': 'dyndns.loopia.se',
        'nsupdatev4': 'ipv4.nsupdate.info',
        'nsupdatev6': 'ipv6.nsupdate.info',
        'ovh': 'www.ovh.com',
        'spdyn': 'update.spdyn.de',
        'strato': 'dyndns.strato.com',
        'noip': 'dynupdate.no-ip.com'
    }

    def __init__(self, account: dict):
        super().__init__(account)

    @staticmethod
    def known_services():
        return  list(DynDNS2._services.keys()) + ['custom']

    def match(account):
        if account.get('service') in DynDNS2._services or (
            account.get('server') is not None and account.get('protocol') in ['dyndns2', 'dyndns1', 'postapi']
        ):
            return True
        else:
            return False

    def execute(self):
        if super().execute():
            protocol = self._account.get('protocol')
            proto = 'https' if self.settings.get('force_ssl', False) else 'http'
            if self.settings.get('service') in self._services:
                url = "%s://%s/nic/update" % (proto, self._services[self.settings.get('service')])
            elif protocol == 'postapi':
                url = "%s://%s" % (proto, self.settings.get('server'))
            else:
                url = "%s://%s/nic/update" % (proto, self.settings.get('server'))

            req_opts = {
                    'auth': HTTPBasicAuth(self.settings.get('username'), self.settings.get('password')),
                    'headers': {
                        'User-Agent': 'OPNsense-dyndns'
                    }
                }
            hostnames = self.settings.get('hostnames')

            if protocol == 'postapi':
                for hostname in hostnames:
                    url_replaced = url.replace('__HOSTNAME__', hostname).replace('__MYIP__', self.current_address)
                    req_opts['url'] = url_replaced
                    req = requests.post(**req_opts)
            else:
                req_opts['params'] = {
                    'hostname': hostnames,
                    'myip': self.current_address,
                    'wildcard': 'ON' if self.settings.get('wildcard', False) else 'NOCHG'
                }
                req_opts['url'] = url
                req = requests.get(**req_opts)

            if req.status_code == 200:
                if self.is_verbose:
                    syslog.syslog(
                        syslog.LOG_NOTICE,
                        "Account %s set new ip %s [%s]" % (self.description, self.current_address, req.text.strip())
                    )

                self.update_state(address=self.current_address, status=req.text.split()[0])
                return True
            else:
                syslog.syslog(
                    syslog.LOG_ERR,
                    "Account %s failed to set new ip %s [%d - %s]" % (
                        self.description, self.current_address, req.status_code, req.text.replace('\n', '')
                    )
                )

        return False
