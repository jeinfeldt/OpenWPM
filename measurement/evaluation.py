'''Contains all objects and functions regarding data evaluation'''
import sqlite3, operator

class DataEvaluator(object):
    '''Encapsulates all evaluation regarding the crawl-data from measuremnt'''
    COOKIE_QRY = '''select site_url, baseDomain from site_visits natural join profile_cookies'''
    COOKIE_NAME_QRY = '''select site_url, baseDomain, profile_cookies.name from site_visits natural join profile_cookies'''
    FLASH_QRY = '''select site_url from site_visits, flash_cookies where site_visits.visit_id == flash_cookies.visit_id'''

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
        '''Evaluates which sites make use of flash cookies'''
        data = {}
        self.cursor.execute(self.FLASH_QRY)
        data['sites'] = [ele[0] for ele in self.cursor.fetchall()]
        data['total_sum'] = len(data['sites'])
        return data

    def rank_third_party_domains(self):
        '''Rank third-party cookie domains based on crawl data (descending)'''
        data = {}
        self.cursor.execute(self.COOKIE_QRY)
        for site_url, ck_domain in self.cursor.fetchall():
            top_domain = self._get_domain(site_url)
            # third-party criteria
            if top_domain != ck_domain:
                frequency = data.get(ck_domain, 0)
                data[ck_domain] = frequency + 1
        # data is sorted based on frequency in descending order
        return sorted(data.iteritems(), key=lambda (k, v): (v, k), reverse=True)

    def rank_third_party_cookie_keys(self):
        '''Rank third-party cookie key based on crawl data (descending)'''
        data = {}
        self.cursor.execute(self.COOKIE_NAME_QRY)
        for site_url, ck_domain, ck_name in self.cursor.fetchall():
            top_domain = self._get_domain(site_url)
            #third-party criteria
            if top_domain != ck_domain:
                frequency = data.get(ck_name, 0)
                data[ck_name] = frequency + 1
        return sorted(data.iteritems(), key=lambda (k, v): (v, k), reverse=True)

    def _eval_cookies(self, operator_func):
        '''Evaluates cookie data based on given operator'''
        data = {}
        self.cursor.execute(self.COOKIE_QRY)
        for site_url, ck_domain in self.cursor.fetchall():
            top_domain = self._get_domain(site_url)
            # criteria: which domain set the cookie?
            if operator_func(top_domain, ck_domain):
                amount = data.get(top_domain, 0)
                data[top_domain] = amount + 1
        data['total_sum'] = reduce(lambda x, y: x + y, data.values())
        return data

    @staticmethod
    def _get_domain(url):
        '''Transforms complete site url to domain e.g.
        http://www.hdm-stuttgart.com to hdm-stuttgart.com'''
        return url.strip("http://www.")

    def close(self):
        '''closes connection to given db'''
        self.connection.close()
