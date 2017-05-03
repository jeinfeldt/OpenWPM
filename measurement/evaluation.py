'''Contains all objects and functions regarding data evaluation'''
import sqlite3, operator

class DataEvaluator(object):
    '''Encapsulates all evaluation regarding the crawl-data from measuremnt'''
    COOKIE_QRY = '''select site_url, baseDomain from site_visits natural join profile_cookies'''

    def __init__(self, db_path):
        self.db_path = db_path
        self.connection = sqlite3.connect(db_path)
        self.cursor = self.connection.cursor()

    def eval_first_party_cookies(self):
        '''Evaluates prevalence of first party cookies based on crawl data.
           first-party: cookies set by top level domain'''
        return self._eval_cookies(operator.eq)

    def eval_third_party_cookies(self):
        '''Evaluates prevalence of third party cookies based on crawl data.
           third-party: cookies set outside of top level domain'''
        return self._eval_cookies(operator.ne)

    def eval_flash_cookies(self):
        pass

    def rank_third_party_domains(self):
        '''Rank most common tracking domains based on dataset (descending)'''
        data = []
        self.cursor.execute(self.COOKIE_QRY)
        for site_url, base_domain in self.cursor.fetchall():
            main_domain = site_url.strip("http://www.")
        return data


    def rank_third_party_cookie_keys(self):
        pass

    def _eval_cookies(self, operator_func):
        '''Evaluates cookie data based on given operator'''
        data = {}
        self.cursor.execute(self.COOKIE_QRY)
        for site_url, base_domain in self.cursor.fetchall():
            main_domain = site_url.strip("http://www.")
            # criteria: which domain set the cookie?
            if operator_func(main_domain, base_domain):
                amount = data.get(main_domain, 0)
                data[main_domain] = amount + 1
        data['total_sum'] = reduce(lambda x, y: x + y, data.values())
        return data

    def _get_domain(self, url):
        '''Transforms complete site url to domain e.g.
        http://www.hdm-stuttgart.com to hdm-stuttgart.com'''
        return url.strip("http://www.")

    def close(self):
        '''closes connection to given db'''
        self.connection.close()
