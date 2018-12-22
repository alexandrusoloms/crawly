import sys
import requests
import numpy as np
import concurrent.futures

from ..proxy import user_agents
from ..proxy import ProxyList


class ConcurrentRequester(object):
    """
    This is a wrapper on python's `requests` library, combining its functionality with
    parallel requests
    """
    def __init__(self, list_of_urls, incognito=True, n_workers=4, verify=True, futures_timeout=3, requests_sleep=3, attempts=9):
        """
        initialises the concurrent requests.

        :param list_of_urls: <list> a _set_ of urls to be scraped - these must be unique
        :param incognito: <bool> when true it will not only return html content if the page size is greater than
                          than a pre-specified amount
        :param n_workers: <int> number of threads to execute calls asynchronously (leave as none for best results)
                          see:  https://docs.python.org/3/library/concurrent.futures.html
        :param verify: <bool> verify certificate (`requests` parameter)
        :param futures_timeout: <int> time until a future (concurrency/ thread) is deemed unsuccessful
        :param requests_sleep: <int> time until a request is deemed unsuccessful
        :param attempts: <int> number of attempts per url
        """
        self.__urls = list_of_urls
        self.__incognito = incognito
        self.__n_workers = n_workers
        self.__verify = verify
        self.__futures_timeout = futures_timeout
        self.__requests_sleep = requests_sleep
        self.__attempts = attempts

        # urls must be unique... so let's check that they are.
        if len(self.__urls) > len(set(self.__urls)):
            raise Exception('URLS are not unique')

        # scraping proxies
        self.__proxy_list = [{'http': ur, 'https': ur} for ur in ProxyList.main(incognito=self.__incognito)]

        self.__n = len(list_of_urls)
        # initialising the results dictionary and setting attempts dictionary to 0
        self.__results_dict = dict()
        self.__attempts_dict = dict()
        for web_page in self.__urls:
            self.__attempts_dict[web_page] = 0
        # proxy list --- if they do not work they must be dropped
        self.__proxy_to_drop = list()

    def __make_requests(self, url, proxy, agent, sleep):
        """
        ordinary requests builder

        :param url: the address of the page as a <string>
        :param proxy: {
                        'http': 'IP:PORT',
                        'https': 'IP:PORT'
                       }
        :param agent: {
                        'User-Agent': <string> content negotiation,
                        'X-Forwarded-For': 'IP' (the IP value is left empty)
                       }
        :return: the raw html of the page as a ``response.content``
        """
        try:
            response = requests.get(url=url, proxies=proxy, headers=agent, timeout=sleep, verify=self.__verify)
            content = response.text

            response.close()
            return proxy, url, content
        except:
            return proxy, url, None

    @staticmethod
    def __get_user_agents(n):
        """
        get ``n`` user agents
        :param n: <int> number of user agents required
        :return: <list> of user agents
        """
        ua_list = list()
        for i in range(n):
            ua_list.append(list(np.random.choice(user_agents, 1)))
        return [x[0] for x in ua_list]

    def run(self):
        """
        initiates the threads, looping indefinitely until all the urls have been requested.

        :return: [{url_1: requests.content_1},
                  {url_2: requests.content_2},
                  {url_3: requests.content_3},
                  ... ]
        """

        while len(self.__results_dict) != self.__n:

            concat_data = list(zip(self.__urls, self.__proxy_list, self.__get_user_agents(n=50)))

            with concurrent.futures.ThreadPoolExecutor(max_workers=self.__n_workers) as executor:
                # initialize operations and mark each future with its url
                future_to_url = {
                    executor.submit(self.__make_requests, u, p, a, self.__requests_sleep): (u, p, a)
                    for (u, p, a) in concat_data
                }
                for future in concurrent.futures.as_completed(future_to_url):
                    the_proxy, web_page, data = future.result(timeout=self.__futures_timeout)
                    if data is not None:
                        if self.__incognito:
                            if sys.getsizeof(data) > 35000:  # greater than 35KB
                                self.__results_dict.update({
                                    web_page: data
                                })
                                self.__urls.remove(web_page)
                            else:
                                self.__attempts_dict[web_page] += 1
                                self.__proxy_list.remove(the_proxy)
                                if self.__attempts_dict[web_page] > self.__attempts:
                                    self.__results_dict.update({
                                        web_page: 'Nothing'
                                    })
                                    self.__urls.remove(web_page)
                    else:
                        self.__attempts_dict[web_page] += 1
                        self.__proxy_list.remove(the_proxy)
                        if self.__attempts_dict[web_page] > self.__attempts:
                            self.__results_dict.update({
                                web_page: 'Nothing'
                            })
                            self.__urls.remove(web_page)

            if len(self.__proxy_list) < 40:
                self.__proxy_list = [{'http': ur, 'https': ur} for ur in ProxyList.main(incognito=self.__incognito)]

            progress = (len(self.__results_dict) / self.__n) * 100
            sys.stdout.write("[INFO]:    Downloading... {0:0.1f}%\r".format(progress))
            sys.stdout.flush()

        return self.__results_dict
