'''Contains all objects and functions regarding data evaluation'''
import sqlite3
import operator
import datetime
import time
from tld import get_tld

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

    FINGERPRINTING_SCRIPTS = '''select script_url, symbol, operation, value,
    arguments from javascript where symbol like \"%%HTMLCanvasElement%%\"
    or symbol like \"%%CanvasRenderingContext2D%%\"'''

    SITE_THIRD_PARTY_REQUESTS = '''select site_url,url,method,referrer,headers
    from site_visits natural join http_requests
    where is_third_party_channel=1'''

    REQUEST_URLS = '''select url from http_requests'''

    HTTP_TIMESTAMPS = '''select site_url, http_requests.time_stamp, http_responses.time_stamp
    from site_visits join http_requests on site_visits.visit_id = http_requests.visit_id
    join http_responses on site_visits.visit_id = http_responses.visit_id
	where http_requests.id = http_responses.id'''

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

    def eval_tracking_context(self, blocklist):
        '''Classifiyes third partys as trackers based on given blocking list (json)
           data{site: {category: num_tracking_context}, avg: num_tracking_context}'''
        data = {}
        total_sum = 0
        categorie_domains = self._map_category_to_domains(blocklist)
        sites_requests = self._map_site_to_request()
        #categories: content, analytics, disconnect, advertising, social
        for site, requests in sites_requests.items():
            req_domains = [x[0] for x in requests]
            for category, domains in categorie_domains.items():
                matches = [x for x in domains if x in "".join(req_domains)]
                total_sum += len(matches)
                data.setdefault(site, []).append((category, len(matches)))
        # calc average number of trackers per page
        data["tracker_avg"] = total_sum / len(sites_requests.keys())
        return data

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

    #TODO: Needs further investment (larger cawl scale) if usable. idea: script name only
    def eval_fingerprint_scripts(self, blacklist):
        '''Matches found js-scripts against blacklist'''
        data = {}
        site_scripts = self.map_site_to_js() # {site: [script...]}
        for site, scripts in site_scripts.items():
            # check if ANY of the found scripts occur in blacklist
            # XXX: Compare netlocation and scriptname?
            matched = [js for js in scripts if js in blacklist]
            for match in matched:
                data.setdefault(match, []).append(site)
        # calc total amount of occurence
        unique_sites = set()
        for sites in data.values():
            unique_sites.update(sites)
        data["total_sum"] = len(unique_sites)
        return data

    def eval_requests(self):
        '''Evaluates number of third-party request and average'''
        data = {}
        sites_requests = self._map_site_to_request()
        num_requests = [len(x) for x in sites_requests.values()]
        data['total_sum'] = reduce(lambda x, y: x + y, num_requests)
        data['request_avg'] = data['total_sum'] / len(sites_requests.keys())
        return data

    def calc_execution_time(self):
        '''Calculates the execution time of the crawl as a formatted string'''
        data = '%sd %sh %smin %ssec'
        time_format = '%Y-%m-%d %H:%M:%S'
        self.cursor.execute(Queries.CRAWL_TIME)
        min_time, max_time = self.cursor.fetchall()[0]
        min_strc = time.strptime(min_time, time_format)
        max_strc = time.strptime(max_time, time_format)
        strc_diff = time.gmtime(time.mktime(max_strc) - time.mktime(min_strc))
        # see doc of time_struct for index information
        return data %(strc_diff[2]-1, strc_diff[3], strc_diff[4], strc_diff[5])

    def calc_pageload(self):
        '''Calculates pageload (initial request to last network activity time for websites'''
        data = {}
        self.cursor.execute(Queries.HTTP_TIMESTAMPS)
        for site, req_timestamp, resp_timestamp in self.cursor.fetchall():
            data.setdefault(site, []).append((req_timestamp, resp_timestamp))
        # analysis of timestamps
        for site, timestamps in data.items():
            min_req = min([x[0] for x in timestamps])
            max_resp = max([x[1] for x in timestamps])
            # calc time difference
            data[site] = self._calc_request_timediff(min_req, max_resp)
        avg = reduce(lambda x, y: x + y, data.values()) / len(data.keys())
        data["loadtime_avg"] = str(avg) + "ms"
        return data

    def detect_canvas_fingerprinting(self):
        '''Detects scripts showing canvas fingerprinting behaviour
           Approach: A 1-million-site Measurement and Analysis'''
        script_symbols = self._map_js_to_symbol()
        _ = script_symbols.items()
        return [js for js, symbols in _ if self._is_fingerprinting(symbols)]

    def detect_general_fingerprinting(self):
        '''Detects scripts showing general fingerprinting behaviour
           Approach: FPDetective: Dusting the Web for Fingerprinters'''
        pass

    def detect_trackers(self, minUsers):
        '''Detects possible user tracking keys based on http request logs per website.
           Approach: Unsupervised Detection of Web Trackers
           minUsers: number of distinct user value pairs to observe'''
        data = {}
        return data

    def rank_third_party_domains(self):
        '''Rank third-party domains based in crawl data (dascending)
           What domain (resource) is most requested?'''
        data = {}
        site_requests = self._map_site_to_request()
        self.cursor.execute(Queries.REQUEST_URLS)
        # x[0] -> tuple is returned from query
        domains = set([self._get_domain(x[0]) for x in self.cursor.fetchall()])
        for domain in domains:
            for site, requests in site_requests.items():
                req_domains = set([self._get_domain(x[0]) for x in requests])
                if domain in req_domains:
                    data.setdefault(domain, []).append(site)
        data = {domain: len(sites) for domain, sites in data.items()}
        return sorted(data.items(), key=lambda (k, v): v, reverse=True)

    def rank_third_party_cookie_domains(self):
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
        return sorted(data.items(), key=lambda (k, v): (v, k), reverse=True)

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
        return sorted(data.items(), key=lambda (k, v): (v, k), reverse=True)

    def map_site_to_js(self):
        '''Collects all found javascript scripts and maps them to site they
           occured on'''
        data = {}
        self.cursor.execute(Queries.JS_SCRIPTS)
        for site_url, script_url in self.cursor.fetchall():
            top_domain = self._get_domain(site_url)
            data.setdefault(top_domain, set([])).add(script_url) # only unique
        # cast set to list
        data = {top_domain: list(scripts) for top_domain, scripts in data.items()}
        return data

    def _map_js_to_symbol(self):
        '''Maps scripts to calls (symbol, operation, arguments) associated
           with canvas fingerprinting'''
        data = {}
       # match sript_url to HTMLCanvasElement and CanvasRendering2DContext calls
        self.cursor.execute(Queries.FINGERPRINTING_SCRIPTS)
        for script, sym, operation, value, args in self.cursor.fetchall():
            data.setdefault(script, []).append((sym, operation, value, args))
        return data

    def _map_site_to_request(self):
        '''Maps sites to their requested (http GET) third-party resources'''
        data = {}
        self.cursor.execute(Queries.SITE_THIRD_PARTY_REQUESTS)
        for site_url, url, method, referrer, headers in self.cursor.fetchall():
            top_domain = self._get_domain(site_url)
            data.setdefault(top_domain, []).append((url, method, referrer, headers))
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
    def _map_category_to_domains(disconnect_dict):
        '''Maps all categories flat to their domains'''
        data = {}
        for category, entries in disconnect_dict['categories'].items():
            #entry [{org: {maindomain: [domain, ...]}]
            domains = set()
            for entry in entries:
                for _, orgdomain in entry.items():
                    domains.update(orgdomain.values()[0])
            data[category] = list(domains)
        return data

    #TODO: 3 and 4 not complete yet
    @staticmethod
    def _is_fingerprinting(calls):
        '''Checks whether or not function call is considered fingerprinting'''
        image_extracted, text_written = False, False
        for sym, opr, val, args in calls:
            # canvas: element height and width set not below 16px
            if "width" in sym or "height" in sym and opr == "set" and int(val) < 16:
                return False
            # context: should not call save, restore or addEventListner
            if "save" in sym or "restore" in sym or "addEventListener" in sym:
                return False
            # canvas: text with min. two colors or min. 10 distinct characters
            if "fillText" in sym and args and len(set(args)) > 12:
                text_written = True
            # canvas: call to toDataURL or getImageData minimum size 16px x 16px
            if "toDataURL" in sym or "getImageData" in sym:
                image_extracted = True
        # both conditions must be met to be considered fingerprinting
        return text_written and image_extracted

    @staticmethod
    def _calc_request_timediff(req_timestmp, res_timestmp):
        '''Calculates the time difference between to timestamps in ms'''
        dates = []
        stmp_format = '%Y-%m-%dT%H:%M:%S'
        for ele in (req_timestmp, res_timestmp):
            stmp, millisec = ele.split(".")
            year, mon, day, hour, mint, sec, _, _, _ = time.strptime(stmp, stmp_format)
            micro = int(millisec.strip("Z"))*1000
            dates.append(datetime.datetime(year, mon, day, hour, mint, sec, micro))
        delta = dates[1] - dates[0]
        return delta.seconds*1000 + delta.microseconds/1000

    @staticmethod
    def _get_domain(url):
        '''Transforms complete site url to domain e.g.
        http://www.hdm-stuttgart.com to hdm-stuttgart.com'''
        # remove protocol
        return get_tld(url, fail_silently=True, fix_protocol=True)

    def close(self):
        '''closes connection to given db'''
        self.connection.close()
