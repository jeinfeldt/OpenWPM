import sqlite3
from tld import get_tld

class Queries(object):
    '''Encapsulates all necessary queries for evaluation as static variables'''

    COOKIE = '''select site_url, baseDomain
    from site_visits natural join profile_cookies'''

    COOKIE_NAME = '''select site_url, baseDomain, profile_cookies.name
    from site_visits natural join profile_cookies'''

    COOKIE_EXPIRY = '''select site_url, baseDomain, name, value, expiry, creationTime
    from site_visits natural join profile_cookies'''

    FLASH = '''select site_url from site_visits, flash_cookies
    where site_visits.visit_id == flash_cookies.visit_id'''

    CRAWL_TIME = '''select min(dtg),max(dtg) from CrawlHistory'''

    LOCALSTORAGE = '''select distinct site_url
    from site_visits natural join javascript
    where symbol like \'%%localStorage%%\''''

    JS_SCRIPTS = '''select site_url, script_url
    from site_visits natural join javascript'''

    CANVAS_SCRIPTS = '''select script_url, symbol, operation, value,
    arguments from javascript where symbol like \"%%HTMLCanvasElement%%\"
    or symbol like \"%%CanvasRenderingContext2D%%\"'''

    FONT_SCRIPTS = '''select script_url, symbol, operation, value,
    arguments from javascript where symbol like \"%%font%%\"'''

    SITE_THIRD_PARTY_REQUESTS = '''select site_url,url,method,referrer,headers
    from site_visits natural join http_requests
    where is_third_party_channel=1'''

    REQUEST_URLS = '''select distinct(url) from http_requests
    where is_third_party_channel=1'''

    REQUEST_TIMESTAMPS = '''select site_url, time_stamp from site_visits join http_requests
    on site_visits.visit_id = http_requests.visit_id'''

    RESPONSE_TIMESTAMPS = '''select site_url, time_stamp from site_visits join http_responses
    on site_visits.visit_id = http_responses.visit_id'''

    USER_IDS = '''select distinct(crawl_id) from crawl'''

    REQUESTS_PER_VISIT_PER_ID = '''select site_url,url,referrer
    from site_visits natural join http_requests
    where crawl_id=%s and visit_id=%s'''

    VISIT_IDS_PER_USER = '''select distinct(visit_id) from site_visits
    where crawl_id=%s'''

    SITE_URLS_VISITED = '''select site_url from site_visits'''

    ID_COOKIES = '''select site_url, name, value, expiry, creationTime
    from profile_cookies natural join site_visits'''

    GET_FAILED_SITES = '''select distinct(arguments)
    from CrawlHistory where command="GET" and  bool_success=-1'''

    NUM_SITES_VISITED = '''select count(distinct(site_url)) from site_visits'''

    RESPONSE_HEADERS = '''select method, headers from http_responses
    where headers like \"%%content-length%%\"'''

    SITES_RESPONSES = '''select site_url, url, headers
    from site_visits natural join http_responses'''

class DataMapper(object):
    '''Abstraction layer between database and dataevaluator'''

    def __init__(self, db_path):
        self.db_path = db_path
        self.connection = sqlite3.connect(db_path)
        self.cursor = self.connection.cursor()

    def close(self):
        '''closes connection to given db'''
        self.connection.close()

    #---------------------------------------------------------------------------
    # CRAWL ANALYSIS
    #---------------------------------------------------------------------------
    def eval_failed_sites(self):
        '''Evaluate which sites caused timeout or failed crawling'''
        self.cursor.execute(Queries.GET_FAILED_SITES)
        return [x[0] for x in self.cursor.fetchall()]

    def eval_visited_sites(self):
        '''Evaluates how many sites have been visited, successfull
        and unsuccessfull'''
        self.cursor.execute(Queries.NUM_SITES_VISITED)
        return self.cursor.fetchone()[0]

    def eval_successful_sites(self):
        '''Evaluates how many sites where visited sucessfully
        (used for internal averaging)'''
        return self.eval_visited_sites() - len(self.eval_failed_sites())

    def fetch_min_maxtime(self):
        '''Fetch min and max timestamps of crawl'''
        self.cursor.execute(Queries.CRAWL_TIME)
        return self.cursor.fetchall()[0]

    #---------------------------------------------------------------------------
    # STORAGE ANALYSIS
    #---------------------------------------------------------------------------
    def fetch_cookies(self):
        '''Fetches cookies values from db'''
        self.cursor.execute(Queries.COOKIE)
        return self.cursor.fetchall()

    def fetch_cookie_expiry(self):
        '''Fetch cookie values with additional expiry'''
        self.cursor.execute(Queries.COOKIE_EXPIRY)
        return self.cursor.fetchall()

    def fetch_cookie_name(self):
        '''Fetch cookie values with additional expiry'''
        self.cursor.execute(Queries.COOKIE_NAME)
        return self.cursor.fetchall()

    def map_localstorage_usage(self):
        '''Fetch sites accessing the localStorage interface'''
        self.cursor.execute(Queries.LOCALSTORAGE)
        return [x[0] for x in self.cursor.fetchall()]

    def map_flash_usage(self):
        '''Fetch sites accessing the Flash interface'''
        self.cursor.execute(Queries.FLASH)
        return [ele[0] for ele in self.cursor.fetchall()]

    @staticmethod
    def _is_id_cookie(cvalue, t_expiry, t_creation):
        '''Checks whether cookie attributes classify as id cookie'''
        check = True
        # note: expiry in sec, creationtime in microsec
        # https://developer.mozilla.org/en-US/docs/Mozilla/Tech/XPCOM/Reference/Interface/nsICookie2
        days_expiry = t_expiry / (60*60*24)
        days_creation = t_creation / (1000*1000*60*60*24)
        # expiration date over 90 days in the future
        if days_expiry - days_creation < 90:
            check = False
        # value longer than 8 characters but smaller 100 characters
        if not 8 <= len(cvalue) <= 100:
            check = False
        # value remains the same throughout the measurement
        # value is different between machines
        return check

    #---------------------------------------------------------------------------
    # HTTP-TRAFFIC ANALYSIS
    #---------------------------------------------------------------------------

    def get_request_urls(self):
        '''Fetches all requested urls'''
        self.cursor.execute(Queries.REQUEST_URLS)
        return self.cursor.fetchall()

    def get_request_timestamps(self):
        '''Fetches requests timestamps'''
        self.cursor.execute(Queries.REQUEST_TIMESTAMPS)
        return self.cursor.fetchall()

    def get_response_timestamps(self):
        '''Fetches response timestamps'''
        self.cursor.execute(Queries.RESPONSE_TIMESTAMPS)
        return self.cursor.fetchall()

    def get_visitids(self, userid):
        '''Fetches correspinding visitids for a user'''
        self.cursor.execute(Queries.VISIT_IDS_PER_USER %userid)
        return [x[0] for x in self.cursor.fetchall()]

    def get_userids(self):
        '''Fetches user ids from db (defined as crawl_id)'''
        self.cursor.execute(Queries.USER_IDS)
        return [x[0] for x in self.cursor.fetchall()]

    def get_visitdata(self, userid, visitid ):
        '''Fetches visit data from db'''
        self.cursor.execute(Queries.REQUESTS_PER_VISIT_PER_ID %(userid, visitid))
        return self.cursor.fetchall()

    def find_id_cookies(self):
        '''Fetch alls cookies identified as ID Cookies
        Approach: Approach: A 1-million-site Measurement and Analysis'''
        data = {}
        self.cursor.execute(Queries.ID_COOKIES)
        for site, cname, cvalue, expiry, creation in self.cursor.fetchall():
            if self._is_id_cookie(cvalue, expiry, creation):
                data.setdefault(self._get_domain(site), []).append((cname, cvalue))
        return data

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

    def map_js_to_symbol_font(self):
        '''Maps scripts to calls (symbol, operation, arguments) associated
           with canvas fingerprinting'''
        data = {}
        # match sript_url to correspinding symbols
        self.cursor.execute(Queries.FONT_SCRIPTS)
        for script, sym, operation, value, args in self.cursor.fetchall():
            data.setdefault(script, []).append((sym, operation, value, args))
        return data

    def map_js_to_symbol_canvas(self):
        '''Maps scripts to calls (symbol, operation, arguments) associated
           with canvas fingerprinting'''
        data = {}
        # match sript_url to correspinding symbols
        self.cursor.execute(Queries.CANVAS_SCRIPTS)
        for script, sym, operation, value, args in self.cursor.fetchall():
            data.setdefault(script, []).append((sym, operation, value, args))
        return data

    def map_site_to_rank(self):
        '''Maps site to correspinding rank, based on order present in site visit
           table (first entry, first of list -> rank 1)'''
        data, rank = {}, 1
        self.cursor.execute(Queries.SITE_URLS_VISITED)
        for site in self.cursor.fetchall():
            data[self._get_domain(site[0])] = rank
            rank += 1
        return data

    def map_site_to_requests(self):
        '''Maps sites to transmitted third-party requests'''
        data = {}
        self.cursor.execute(Queries.SITE_THIRD_PARTY_REQUESTS)
        for site_url, url, method, referrer, headers in self.cursor.fetchall():
            top_domain = self._get_domain(site_url)
            data.setdefault(top_domain, []).append((url, method, referrer, headers))
        return data

    def map_site_to_responses(self):
        '''Maps sites to received thiry-party responses'''
        data = {}
        self.cursor.execute(Queries.SITES_RESPONSES)
        for site_url, url, headers in self.cursor.fetchall():
            top_domain = self._get_domain(site_url)
            if top_domain != self._get_domain(url): # third party criteria
                data.setdefault(top_domain, []).append((url, headers))
        return data

    @staticmethod
    def _get_domain(url):
        '''Transforms complete site url to domain e.g.
        http://www.hdm-stuttgart.com to hdm-stuttgart.com'''
        # remove protocol
        return get_tld(url, fail_silently=True, fix_protocol=True)
