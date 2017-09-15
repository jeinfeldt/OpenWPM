'''Contains all objects and functions regarding data evaluation'''
import sqlite3
import operator
import datetime
import time
import urlparse
import os
import ast
from tld import get_tld

class Queries(object):
    '''Encapsulates all necessary queries for evaluation as static variables'''

    COOKIE = '''select site_url, baseDomain
    from site_visits natural join profile_cookies'''

    COOKIE_NAME = '''select site_url, baseDomain, profile_cookies.name
    from site_visits natural join profile_cookies'''

    COOKIE_EXPIRY = '''select site_url, baseDomain, name, value, expiry, creationTime
    from site_visits natural join profile_cookies;'''

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

class DataEvaluator(object):
    '''Encapsulates all evaluation regarding the crawl-data from measurement'''

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
    def eval_crawlsuccess(self):
        '''Evaluates number of successfull commands and timeouts during crawl'''
        data = {}
        data['num_timeouts'] = len(self._eval_failed_sites())
        data['num_pages'] = self._eval_visited_sites()
        rate = (float(data['num_timeouts']) / float(data['num_pages'])) * 100.0
        data['rate_timeouts'] = rate
        return data

    def eval_crawltype(self):
        '''Evalautes the type of crawl that was performed based on db names
           (vanilla, ghostery, disconnect, adblock)'''
        return os.path.basename(self.db_path).split("-")[2]

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

    def _eval_failed_sites(self):
        '''Evaluate which sites caused timeout or failed crawling'''
        self.cursor.execute(Queries.GET_FAILED_SITES)
        return [x[0] for x in self.cursor.fetchall()]

    def _eval_visited_sites(self):
        '''Evaluates how many sites have been visited, successfull
        or unsuccessfull'''
        self.cursor.execute(Queries.NUM_SITES_VISITED)
        return self.cursor.fetchone()[0]

    #---------------------------------------------------------------------------
    # STORAGE ANALYSIS
    #---------------------------------------------------------------------------
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
        self.cursor.execute(Queries.FLASH)
        data['sites'] = [ele[0] for ele in self.cursor.fetchall()]
        data['total_sum'] = len(data['sites'])
        return data

    #TODO
    def eval_tracking_cookies(self):
        '''Evaluates prevalence of third party TRACKING cookies based on crawl data.
           third-party: cookies set outside of top level domain
           tracking:    expiry > 1 day, value > 35 characters
           Approach: TrackAdvisor: Taking Back Browsing Privacy From Third-Party Trackers'''
        data = {}
        return data

    def eval_localstorage_usage(self):
        '''Evaluates the usage of localstorage across unique sites'''
        data = {}
        self.cursor.execute(Queries.LOCALSTORAGE)
        data['sites'] = [self._get_domain(x[0]) for x in self.cursor.fetchall()]
        data['total_sum'] = len(data['sites'])
        return data

    def rank_third_party_cookie_domains(self, amount=10):
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
        return sorted(data.items(), key=lambda (k, v): (v, k), reverse=True)[:amount]

    def rank_third_party_cookie_keys(self, amount=10):
        '''Rank third-party cookie key based on crawl data (descending)'''
        data = {}
        self.cursor.execute(Queries.COOKIE_NAME)
        for site_url, ck_domain, ck_name in self.cursor.fetchall():
            top_domain = self._get_domain(site_url)
            #third-party criteria
            if top_domain != ck_domain:
                frequency = data.get(ck_name, 0)
                data[ck_name] = frequency + 1
        return sorted(data.items(), key=lambda (k, v): (v, k), reverse=True)[:amount]

    def calc_avg_cookie_lifetime(self):
        '''Calcualte average lifetime of third-party and first-party cookies
        in days'''
        data, thirdpty_expiry, firstpty_expiry = {}, [], []
        self.cursor.execute(Queries.COOKIE_EXPIRY)
        for site_url, ck_domain, ck_name, ck_value, expiry, created in self.cursor.fetchall():
            top_domain = self._get_domain(site_url)
            expiry = expiry / (60*60*24) # in sec
            created = created / (1000*1000*60*60*24) # in microsec
            # distinguish cookies
            if top_domain != ck_domain: # third-party
                thirdpty_expiry.append(expiry - created)
            else: #first-party
                firstpty_expiry.append(expiry - created)
        # calculate average values
        fp_avg = reduce(lambda x, y: x + y, firstpty_expiry)
        tp_avg = reduce(lambda x, y: x + y, thirdpty_expiry)
        data['fp_expiry_avg'] = fp_avg / len(firstpty_expiry)
        data['tp_expiry_avg'] = tp_avg / len(thirdpty_expiry)
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
        data['cookie_avg'] = data['total_sum'] / len(data.keys())
        return data

    #---------------------------------------------------------------------------
    # HTTP-TRAFFIC ANALYSIS
    #---------------------------------------------------------------------------
    def eval_requests(self):
        '''Evaluates number of third-party request and average'''
        data = {}
        sites_requests = self._map_site_to_requests()
        num_requests = [len(x) for x in sites_requests.values()]
        data['total_sum'] = reduce(lambda x, y: x + y, num_requests)
        data['request_avg'] = data['total_sum'] / len(sites_requests.keys())
        return data

    def eval_tracking_context(self, blocklist):
        '''Classifiyes third partys as trackers based on given blocking list (json)
        maps sites to amount of domains (NOT resources) that would have been blocked'''
        data, uniquedoms = {}, set()
        categorie_domains = self._map_category_to_domains(blocklist)
        sites_requests = self._map_site_to_requests()
        blocked = [domain for l in categorie_domains.values() for domain in l]
        # check all blocked domains that occur in site request urls
        for site, requests in sites_requests.items():
            requrls = [tup[0] for tup in requests]
            matches = [dom for dom in blocked if dom in "".join(requrls)]
            if len(matches) > 0:
                data[site] = len(matches)
                uniquedoms.update(matches)
        # calc total sum, unique trackers and avg per site
        data["total_sum"] = reduce(lambda x, y: x + y, data.values())
        data["unique_trackers"] = list(uniquedoms)
        data["tracker_avg"] = data["total_sum"] / len(sites_requests.keys())
        return data

    def eval_response_traffic(self):
        '''Evaluates amount of received bytes based on content length
        field in response headers'''
        data = {}
        sites_responses = self._map_site_to_responses()
        for site, responses in sites_responses.items():
            headers = [ast.literal_eval(tup[1]) for tup in responses]
            fields = [y for x in headers for y in x if y[0] == "Content-Length"]
            clengths = [x[1] for x in fields if len(x) == 2 and x[1].isdigit()]
            if len(clengths) > 0:
                data[site] = reduce(lambda x, y: int(x) + int(y), clengths)
        # calc total sum and average
        data['total_sum'] = reduce(lambda x, y: int(x) + int(y), data.values())
        data['byte_avg'] = data['total_sum'] / len(sites_responses.keys())
        # convert to kB
        data['total_sum'] = str(data['total_sum']/1000) + "kB"
        data['byte_avg'] = str(data['byte_avg']/1000) + "kB"
        return data

    def calc_pageload(self):
        '''Calculates pageload time (in milliseconds) according to timestamp between initial
        request to last response websites Note: Failed sites of the crawl are ignored'''
        data, site_reqstamps, site_respstamps = {}, {}, {}
        failed = self._eval_failed_sites()
        # map request timestamps
        self.cursor.execute(Queries.REQUEST_TIMESTAMPS)
        for site, timestamp in self.cursor.fetchall():
            if site not in failed:
                site_reqstamps.setdefault(site, []).append(timestamp)
        # map response timestamps
        self.cursor.execute(Queries.RESPONSE_TIMESTAMPS)
        for site, timestamp in self.cursor.fetchall():
            if site not in failed:
                site_respstamps.setdefault(site, []).append(timestamp)
        # calc time difference first request, last response
        for site in site_respstamps:
            min_req = min(site_reqstamps[site])
            max_resp = max(site_respstamps[site])
            data[site] = self._calc_request_timediff(min_req, max_resp)
        avg = reduce(lambda x, y: x + y, data.values()) / len(data.keys())
        data["loadtime_avg"] = avg
        return data

    def detect_cookie_syncing(self):
        '''Detects cookie syncing behaviour in http traffic logs
           Approach: A 1-million-site Measurement and Analysis'''
        data = {}
        site_cookies = self._find_id_cookies()
        site_requests = self._map_site_to_requests()
        for site, cookies in site_cookies.items():
            #are ids leaked in requested third party urls or referers?
            requests = site_requests.get(site, [])
            urls = [tpl[0] for tpl in requests] + list(set([tpl[2] for tpl in requests]))
            cvalues = [tpl[1] for tpl in cookies]
            matches = [url for url in urls if len([x for x in cvalues if x in url]) > 0]
            data[site] = list(set([self._get_domain(x) for x in matches]))
        # total amount of sites leaking cookie ids
        data['total_sum'] = len([x for x in data.values() if len(x) > 0])
        return data

    def detect_trackers(self, min_users=3):
        '''Detects possible user tracking keys based on http request logs per website.
           Approach: Unsupervised Detection of Web Trackers
           IMPORTANT: Expects datainput in certain format
           minUsers: number of distinct user value pairs to observe'''
        data = set()
        userdata = self._prepare_detection_data()
        pairs = self._find_user_tracking_pairs(userdata, min_users)
        # map detected keys to site they occured on
        for _, visitdata in userdata[0].items():
            urls = [url for v in visitdata for url in list(v['urls'])]
            # fetch urls which contains marked header value
            key_value = [pair[0]+'='+pair[1] for pair in pairs]
            matches = [url for url in urls for pair in key_value if pair in url]
            for match in matches:
                data.add(self._get_subdomain(match) + "." + self._get_domain(match))
        return list(data)

    def rank_third_party_prominence(self, amount=10):
        '''Ranks third-party domains based on suggested prominence metric
           Approach: A 1-million-site Measurement and Analysis'''
        data = {}
        sites_rank = self._map_site_to_rank()
        sites_requests = self._map_site_to_requests()
        domains = self._get_requested_domains()
        for dom in domains:
            # prominence: sum of all 1/rank(site) where domain is present
            items = sites_requests.items()
            ranks = [sites_rank[site] for site, req in items if self._is_domain_present(dom, req)]
            data[dom] = reduce(lambda x, y: x + y, [1.0/x for x in ranks])
        return sorted(data.items(), key=lambda (k, v): v, reverse=True)[:amount]

    def rank_third_party_domains(self, amount=10):
        '''Rank third-party domains based in crawl data (dascending)
           What domain (resource) is most requested? Based on prevalence'''
        data = {}
        site_requests = self._map_site_to_requests()
        domains = self._get_requested_domains()
        items = site_requests.items()
        for domain in domains:
            # fetch sites which request domain
            sites = [site for site, reqs in items if self._is_domain_present(domain, reqs)]
            data[domain] = len(sites)
        return sorted(data.items(), key=lambda (k, v): v, reverse=True)[:amount]

    def rank_organisation_reach(self, disconnect_dict):
        '''Ranks the reach of an organisation based on the disconnect blocking
           list which contains organisations with their associated domains
           Approach: Tracking the Trackers'''
        data = {}
        org_domains = self._map_org_to_domains(disconnect_dict)
        org_orgurl = self._map_org_to_orgurl(disconnect_dict)
        domains = self._get_requested_domains()
        site_requests = self._map_site_to_requests()
        # filter only orgnames present in crawl
        items = org_orgurl.items()
        orgnames = [org for org, url in items if self._get_domain(url) in domains]
        # check for any associated domains in requests
        items = site_requests.items()
        for orgname in orgnames:
            amount = set()
            for domain in org_domains[orgname]:
                amount.update([site for site, reqs in items if self._is_domain_present(domain, reqs)])
            data[orgname] = len(amount)
        return sorted(data.items(), key=lambda (k, v): v, reverse=True)[:10]

    def _prepare_detection_data(self):
        '''Prepares dict to check for stable user identifiers
           Users are represented by dicts in lists where site is mapped to a list
           containing a dict per visit, containing requests and extracted http pairs'''
        userdata = []
        # fetch request urls per user per visit
        for userid in self._get_userids():
            sitedata = {}
            for visitid in self._get_visitids(userid):
                requests, site, visitdata = set(), "", {}
                self.cursor.execute(Queries.REQUESTS_PER_VISIT_PER_ID %(userid, visitid))
                for site_url, url, referrer in self.cursor.fetchall():
                    site = site_url
                    requests.update([url, referrer])
                visitdata['urls'] = requests
                # extract keys and values
                visitdata['extracted'] = self._extract_http_pairs(list(requests))
                sitedata.setdefault(site, []).append(visitdata)
            userdata.append(sitedata)
        return userdata

    def _get_visitids(self, userid):
        '''Fetches correspinding visitids for a user'''
        self.cursor.execute(Queries.VISIT_IDS_PER_USER %userid)
        return [x[0] for x in self.cursor.fetchall()]

    def _get_userids(self):
        '''Fetches user ids from db (defined as crawl_id)'''
        self.cursor.execute(Queries.USER_IDS)
        return [x[0] for x in self.cursor.fetchall()]

    def _get_requested_domains(self):
        '''Fetches all requested unique top domains during crawl'''
        self.cursor.execute(Queries.REQUEST_URLS)
        # x[0] -> tuple is returned from query
        return list(set([self._get_domain(x[0]) for x in self.cursor.fetchall()]))

    def _is_domain_present(self, domain, requests):
        '''Checks whether given third party is present in the given request
        requests of the site'''
        req_domains = set([self._get_domain(req[0]) for req in requests])
        return True if domain in req_domains else False

    def _find_id_cookies(self):
        '''Fetch alls cookies identified as ID Cookies
        Approach: Approach: A 1-million-site Measurement and Analysis'''
        data = {}
        self.cursor.execute(Queries.ID_COOKIES)
        for site, cname, cvalue, expiry, creation in self.cursor.fetchall():
            if self._is_id_cookie(cvalue, expiry, creation):
                data.setdefault(self._get_domain(site), []).append((cname, cvalue))
        return data

    @staticmethod
    def _find_user_tracking_pairs(userdata, min_users):
        '''Identifies possible user tracking keys in http pairs'''
        userpairs = []
        num_visits = len(userdata[0].values()[0])
        num_users = len(userdata)
        # find pairs which are stable across visits for a user
        for userdict in userdata:
            pairs = [pair for visit in userdict.values()[0] for pair in visit['extracted']]
            matches = set([x for x in pairs if pairs.count(x) == num_visits])
            userpairs.append(list(matches))
        # find pairs which have different values for each user
        keys = [pair[0] for user in userpairs for pair in user]
        check_key = lambda tpl: keys.count(tpl[0]) == num_users # every user has key
        # key should have more distinct values than threshold
        filter_tup = lambda key: [y for x in userpairs for y in x if y[0] == key]
        distinct_vals = lambda key: len(set([x[1] for x in filter_tup(key)]))
        check_val = lambda tpl: distinct_vals(tpl[0]) >= min_users
        # consider threshold for pair value
        return list(set([y for x in userpairs for y in x if check_key(y) and check_val(y)]))

    @staticmethod
    def _map_category_to_domains(disconnect_dict):
        '''Maps all categories flat to their domains'''
        data = {}
        for category, entries in disconnect_dict['categories'].items():
            #entry [{org: {maindomain: [domain, ...]}]
            domains = set()
            for entry in entries:
                for _, orgurl in entry.items():
                    domains.update(orgurl.values()[0])
            data[category] = list(domains)
        return data

    @staticmethod
    def _map_org_to_orgurl(disconnect_dict):
        '''Maps all categories flat to their domains'''
        data = {}
        for entries in disconnect_dict['categories'].values():
            for entry in entries:
                for orgname, orgurl in entry.items():
                    data[orgname] = orgurl.keys()[0]
        return data

    @staticmethod
    def _map_org_to_domains(disconnect_dict):
        '''Maps all organisations flat to the associated domains'''
        data = {}
        for entries in disconnect_dict['categories'].values():
            for entry in entries:
                for orgname, orgurl in entry.items():
                    data[orgname] = orgurl.values()[0]
        return data

    @staticmethod
    def _extract_http_pairs(urls):
        '''Extracts url parameters as list of key value touples
           http://www.acme.com/query?key1=X&key2=Y -> [(key1, X), (key2, Y)]'''
        pairs = set()
        if not isinstance(urls, list):
            urls = [urls]
        for url in urls:
            queryparams = urlparse.urlparse(url).query.split("&")
            parsed = [tuple(x.split("=")) for x in queryparams if ''.join(queryparams) != ""]
            pairs.update(parsed)
        return list(pairs)

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

    #---------------------------------------------------------------------------
    # FINGERPRINTING ANALYSIS
    #---------------------------------------------------------------------------
    def eval_fingerprint_scripts(self, blacklist):
        '''Matches found js-scripts against blacklist'''
        data = {}
        site_scripts = self._map_site_to_js() # {site: [script...]}
        _ = [x for l in blacklist.values() for x in l]
        fptpl = [(self._get_domain(x), self._get_resource_name(x)) for x in _]
        # check if ANY of the found scripts occur in blacklist
        for site, scripts in site_scripts.items():
            sitetpl = [(self._get_domain(js), self._get_resource_name(js)) for js in scripts]
            matched = [tpl for tpl in fptpl if tpl in sitetpl]
            for match in matched:
                data.setdefault(match, []).append(site)
        # calc total amount of occurence
        unique_sites = set([site for l in data.values() for site in l])
        data["sites"] = list(unique_sites)
        data["total_sum"] = len(unique_sites)
        return data

    def detect_canvas_fingerprinting(self):
        '''Detects scripts showing canvas fingerprinting behaviour
           Approach: A 1-million-site Measurement and Analysis'''
        script_symbols = self._map_js_to_symbol(Queries.CANVAS_SCRIPTS)
        items = script_symbols.items()
        return [js for js, sym in items if self._is_canvas_fingerprinting(sym)]

    def detect_font_fingerprinting(self):
        '''Detects scripts showing general fingerprinting (font probing) behaviour
           Approach: FPDetective: Dusting the Web for Fingerprinters'''
        script_symbols = self._map_js_to_symbol(Queries.FONT_SCRIPTS)
        items = script_symbols.items()
        return [js for js, sym in items if self._is_font_fingerprinting(sym)]

    #TODO: 3 and 4 not complete yet
    @staticmethod
    def _is_canvas_fingerprinting(calls):
        '''Checks if function calls resemble canvas fingerprinting behaviour
           Approach: A 1-million-site Measurement and Analysis'''
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
    def _is_font_fingerprinting(calls):
        '''Checks if function calls resemble font fingerprinting behaviour
           Approach: FPDetective: Dusting the Web for Fingerprinters'''
        threshold = 30
        matches = set([val for _, op, val, _ in calls if op == 'set'])
        return True if len(matches) >= threshold else False

    #---------------------------------------------------------------------------
    # UTILITIES
    #---------------------------------------------------------------------------
    @staticmethod
    def discover_new_trackers(detected, blacklist):
        '''Discovers new trackers by matching detected list of tracking
           domains against given domain list'''
        _ = DataEvaluator._map_category_to_domains(blacklist)
        blocked = [DataEvaluator._get_domain(x) for l in _.values() for x in l]
        return [x for x in detected['domains'] if x not in blocked]

    def _map_site_to_js(self):
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

    def _map_js_to_symbol(self, query):
        '''Maps scripts to calls (symbol, operation, arguments) associated
           with canvas fingerprinting'''
        data = {}
        # match sript_url to correspinding symbols
        self.cursor.execute(query)
        for script, sym, operation, value, args in self.cursor.fetchall():
            data.setdefault(script, []).append((sym, operation, value, args))
        return data

    def _map_site_to_rank(self):
        '''Maps site to correspinding rank, based on order present in site visit
           table (first entry, first of list -> rank 1)'''
        data, rank = {}, 1
        self.cursor.execute(Queries.SITE_URLS_VISITED)
        for site in self.cursor.fetchall():
            data[self._get_domain(site[0])] = rank
            rank += 1
        return data

    def _map_site_to_requests(self):
        '''Maps sites to transmitted third-party requests'''
        data = {}
        self.cursor.execute(Queries.SITE_THIRD_PARTY_REQUESTS)
        for site_url, url, method, referrer, headers in self.cursor.fetchall():
            top_domain = self._get_domain(site_url)
            data.setdefault(top_domain, []).append((url, method, referrer, headers))
        return data

    def _map_site_to_responses(self):
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

    @staticmethod
    def _get_subdomain(url):
        '''Get a main domain with a subdomain'''
        res = get_tld(url, fail_silently=True, fix_protocol=True, as_object=True)
        return res.subdomain.lstrip("www.")

    @staticmethod
    def _get_resource_name(url):
        '''Get requested resource name from complete url e.g.
           http://www.example.com/js/peter/script.js yields script.js'''
        return urlparse.urlparse(url).path.split("/")[-1]
