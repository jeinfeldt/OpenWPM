'''Contains all objects and functions regarding data evaluation'''
import sqlite3, operator, time, json

class Queries(object):
    '''Encapsulates all necessary queries for evaluation as static variables'''

    COOKIE = '''select site_url, baseDomain
                    from site_visits natural join profile_cookies'''

    COOKIE_NAME = '''select site_url, baseDomain, profile_cookies.name
                         from site_visits natural join profile_cookies'''

    FLASH = '''select site_url from site_visits, flash_cookies
                   where site_visits.visit_id == flash_cookies.visit_id'''

    CRAWL_TIME = '''select min(dtg),max(dtg) from CrawlHistory'''

    LOCALSTORAGE = '''select distinct site_url
                          from site_visits natural join javascript
                          where symbol like \'%%localStorage%%\''''

    JS_SCRIPTS = '''select site_url, script_url
                    from site_visits natural join javascript'''

class DataEvaluator(object):
    '''Encapsulates all evaluation regarding the crawl-data from measuremnt'''

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

    #TODO: Needs further investment (larger cawl scale) if usable
    def eval_flash_cookies(self):
        '''Evaluates which sites make use of flash cookies'''
        data = {}
        self.cursor.execute(Queries.FLASH)
        data['sites'] = [ele[0] for ele in self.cursor.fetchall()]
        data['total_sum'] = len(data['sites'])
        return data

    def eval_localstorage_usage(self):
        '''Evaluates the usage of localstorage across unique sites'''
        data = {}
        self.cursor.execute(Queries.LOCALSTORAGE)
        data['sites'] = [self._get_domain(x[0]) for x in self.cursor.fetchall()]
        data['total_sum'] = len(data['sites'])
        return data

    def calc_execution_time(self):
        '''Calculates the execution time of the crawl as a formatted string'''
        self.cursor.execute(Queries.CRAWL_TIME)
        data = '%sd %sh %smin %ssec'
        time_format = '%Y-%m-%d %H:%M:%S'
        min_time, max_time = self.cursor.fetchall()[0]
        min_strc = time.strptime(min_time, time_format)
        max_strc = time.strptime(max_time, time_format)
        strc_diff = time.gmtime(time.mktime(max_strc) - time.mktime(min_strc))
        # see doc of time_struct for index information
        return data %(strc_diff[2]-1, strc_diff[3], strc_diff[4], strc_diff[5])

    #TODO: Needs further investment (larger cawl scale) if usable. idea: script name only
    def eval_fingerprint_scripts(self, listpath):
        '''Matches available js-scripts against given fingerprint scripts
           Note: listpath file should be json'''
        data = {}
        found_dic = self.map_js_scripts() # {site: [script...]}
        blacklist_dic = self._load_json(listpath) #{type: [script...]}
        for site, found_scripts in found_dic.items():
            for fp_type, blacklist in blacklist_dic.items():
                # check if ANY of the found scripts occur in blacklist
                matched = [x for x in found_scripts if x in blacklist]
                if len(matched) > 0:
                    sites = data.get(fp_type, [])
                    sites.append(site)
                    data[fp_type] = sites
        # calc total amount of occurence
        total_sites = set()
        for found in data.values():
            total_sites.update(found)
        data["total_sum"] = len(total_sites)
        return data

    def detect_canvas_fingerprinting(self):
        '''Detects scripts showing canvas fingerprinting behaviour
           Approach: A 1-million-site Measurement and Analysis'''
           # match sript_url to HTMLCanvasElement and CanvasRendering2DContext calls
           # canvas elemnt height and width set not below 16px
           # script should not call save, restore or addEventListner
           # call to toDataURL or getImageData minimum size 16px x 16px.
        pass

    def detect_general_fingerprinting(self):
        '''Detects scripts showing general fingerprinting behaviour
           Approach: FPDetective: Dusting the Web for Fingerprinters'''
        pass

    def rank_third_party_domains(self):
        '''Rank third-party cookie domains based on crawl data (descending)'''
        data = {}
        self.cursor.execute(Queries.COOKIE)
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
        self.cursor.execute(Queries.COOKIE_NAME)
        for site_url, ck_domain, ck_name in self.cursor.fetchall():
            top_domain = self._get_domain(site_url)
            #third-party criteria
            if top_domain != ck_domain:
                frequency = data.get(ck_name, 0)
                data[ck_name] = frequency + 1
        return sorted(data.iteritems(), key=lambda (k, v): (v, k), reverse=True)

    def map_js_scripts(self):
        '''Collects all found javascript scripts and maps them to site they
           occured on'''
        data = {}
        self.cursor.execute(Queries.JS_SCRIPTS)
        for site_url, script_url in self.cursor.fetchall():
            top_domain = self._get_domain(site_url)
            script_domain = self._get_domain(script_url)
            # only unique scripts -> set
            scripts = data.get(top_domain, set([]))
            scripts.add(script_domain)
            data[top_domain] = scripts
        # cast set to list
        for top_domain, scripts in data.items():
            data[top_domain] = list(scripts)
        return data

    def _eval_cookies(self, operator_func):
        '''Evaluates cookie data based on given operator'''
        data = {}
        self.cursor.execute(Queries.COOKIE)
        for site_url, ck_domain in self.cursor.fetchall():
            top_domain = self._get_domain(site_url)
            # criteria: which domain set the cookie?
            if operator_func(top_domain, ck_domain):
                amount = data.get(top_domain, 0)
                data[top_domain] = amount + 1
        data['total_sum'] = reduce(lambda x, y: x + y, data.values())
        return data

    @staticmethod
    def _load_json(path):
        '''Reads json file ignoring comments'''
        ignore = ["__comment"]
        with open(path) as raw:
            data = json.load(raw)
            for ele in ignore:
                if ele in data:
                    data.pop(ele)
        return data

    @staticmethod
    def _get_domain(url):
        '''Transforms complete site url to domain e.g.
        http://www.hdm-stuttgart.com to hdm-stuttgart.com'''
        # remove protocol
        domain = ""
        protocols = ["http://", "https://"]
        for ele in protocols:
            if ele in url:
                domain = url.lstrip(ele)
        return domain.lstrip("www.")

    def close(self):
        '''closes connection to given db'''
        self.connection.close()
