import numpy as np
import requests
from bs4 import BeautifulSoup

from .user_agents import user_agents


class ProxyList(object):

    __POST_METHOD = 'post'
    __GET_METHOD = 'get'
    __PROXY_URL = ['https://www.us-proxy.org/', 'https://www.sslproxies.org/',
                   'https://free-proxy-list.net/uk-proxy.html', 'https://free-proxy-list.net/anonymous-proxy.html']

    @staticmethod
    def __make_request(url, method, **kwargs):
        """make a http request to a ``url``

        :param url: the address
        :param method: the HTTP method ('get', 'post')
        :param kwargs: any other parameters that go into the ``requests`` builder
        :return:
        """
        content = None
        # some times the proxies fail, so a while loop is employed to
        # ensure that a correct html is returned
        while not content:
            try:
                __headers = np.random.choice(user_agents, 1)[0]
                if method == ProxyList.__POST_METHOD:
                    response = requests.post(url, method, **kwargs)
                else:
                    response = requests.get(url, method, timeout=5, **kwargs)

                if 'html' or 'text' in response.headers['Content-Type']:
                    content = response.content
                    if len(content) < 5000:  # <-- anything below this is a captcha.
                        content = None
                    response.close()
            except:
                # in the event ``response`` is created and not closed.
                if 'response' in locals():
                    response.close()
                continue
        return content

    @staticmethod
    def __parse_html(raw_html, incognito=False):
        """
        simply parses the proxy web page for the proxies

        :param raw_html: the object returned by the ``_make_request`` method.
        :param incognito: <bool> specifying if only 'elite proxies' are wanted (recommended)
        :return: a set of proxies
        """
        soup = BeautifulSoup(raw_html, 'html.parser')
        results_list = [
            x.findAll('td') for x in soup.find(
                'div', attrs={'class': 'table-responsive'}).find('table').findAll('tr')
        ]
        results_list = list(
            filter(lambda x: x != [], results_list)
        )
        ip_addresses = [x.text for y in results_list for x in y][::8]
        ports = [x.text for y in results_list for x in y][1::8]
        type_of_proxy = [x.text for y in results_list for x in y][4::8]

        if incognito:
            proxies = set(
                ip_addresses[x] + ':' + ports[x]
                for x in range(len(ip_addresses)) if type_of_proxy[x] == 'elite proxy'
            )
            return proxies

        else:
            proxies = set(
                ip_addresses[x] + ':' + ports[x] for x in range(len(ip_addresses)) if type_of_proxy[x] != 'transparent'
            )
            return proxies

    @classmethod
    def main(cls, incognito, **kwargs):
        """

        :param incognito: <bool> set to True for only 'elite proxies'.
        :param kwargs: any other params that go into the requests builder.
        :return:
        """
        set_of_proxies = set()

        for url in ProxyList.__PROXY_URL:

            raw_html = cls.__make_request(
                url=url,
                method=ProxyList.__GET_METHOD,
                **kwargs)
            proxies = cls.__parse_html(raw_html=raw_html, incognito=incognito)
            set_of_proxies.update(proxies)
        set_of_proxies = list(set_of_proxies)
        np.random.shuffle(set_of_proxies)
        return set_of_proxies
