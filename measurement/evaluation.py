'''Contains all objects and functions regarding data evaluation'''
import operator
import datetime
import time
import urlparse
import os
import ast
from tld import get_tld
from datamapper import DataMapper

class DataEvaluator(object):
    '''Encapsulates all evaluation regarding the crawl-data from measurement'''

    def __init__(self, db_path):
        self.mapper = DataMapper(db_path)

    def close(self):
        '''closes connection to given db'''
        self.mapper.close()

    #---------------------------------------------------------------------------
    # CRAWL ANALYSIS
    #---------------------------------------------------------------------------
    def eval_crawlsuccess(self):
        '''Evaluates number of successfull commands and timeouts during crawl'''
        data = {}
        data['num_timeouts'] = len(self.mapper.eval_failed_sites())
        data['num_pages'] = self.mapper.eval_visited_sites()
        rate = (float(data['num_timeouts']) / float(data['num_pages'])) * 100.0
        data['rate_timeouts'] = rate
        return data

    def eval_crawltype(self):
        '''Evalautes the type of crawl that was performed based on db names
           (vanilla, ghostery, disconnect, adblock)'''
        return os.path.basename(self.mapper.db_path).split("-")[2]

    def calc_execution_time(self):
        '''Calculates the execution time of the crawl as a formatted string'''
        data = '%sd %sh %smin %ssec'
        time_format = '%Y-%m-%d %H:%M:%S'
        min_time, max_time = self.mapper.fetch_min_maxtime()
        min_strc = time.strptime(min_time, time_format)
        max_strc = time.strptime(max_time, time_format)
        strc_diff = time.gmtime(time.mktime(max_strc) - time.mktime(min_strc))
        # see doc of time_struct for index information
        return data %(strc_diff[2]-1, strc_diff[3], strc_diff[4], strc_diff[5])

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

    def eval_tracking_cookies(self):
        '''Evaluates prevalence of tracking cookies based on crawl data.
           third-party: cookies set outside of top level domain
           tracking:    expiry > 1 day, value > 35 characters
           Approach: TrackAdvisor: Taking Back Browsing Privacy From Third-Party Trackers'''
        data = {}
        cookies = self.mapper.fetch_cookie_expiry()
        for site_url, ck_domain, _, ck_value, expiry, created in cookies:
            top_domain = self._get_domain(site_url)
            expiry = expiry / (60*60*24) # in sec
            created = created / (1000*1000*60*60*24) # in microsec
            lifetime = expiry - created
            if top_domain != ck_domain and len(ck_value) > 35 and lifetime > 1:
                amount = data.get(top_domain, 0)
                data[top_domain] = amount + 1
        # summary of data
        data['total_sum'] = reduce(lambda x, y: x + y, data.values())
        data['tracking_cookie_avg'] = data['total_sum'] / self.mapper.eval_successful_sites()
        return data

    def eval_flash_cookies(self):
        '''Evaluates which sites make use of flash cookies'''
        data = {}
        data['sites'] = self.mapper.map_flash_usage()
        data['total_sum'] = len(data['sites'])
        data['site_percentage'] = float(len(data['sites'])) / float(self.mapper.eval_successful_sites())
        return data

    def eval_localstorage_usage(self):
        '''Evaluates the usage of localstorage across unique sites'''
        data = {}
        data['sites'] = [self._get_domain(x[0]) for x in self.mapper.map_localstorage_usage()]
        data['total_sum'] = len(data['sites'])
        data['site_percentage'] = float(len(data['sites'])) / float(self.mapper.eval_successful_sites())
        return data

    def rank_third_party_cookie_domains(self, amount=10):
        '''Rank third-party cookie domains based on crawl data (descending)'''
        data = {}
        for site_url, ck_domain in self.mapper.fetch_cookies():
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
        for site_url, ck_domain, ck_name in self.mapper.fetch_cookie_name():
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
        for site_url, ck_domain, _, _, expiry, created in self.mapper.fetch_cookie_expiry():
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
        for site_url, ck_domain in self.mapper.fetch_cookies():
            top_domain = self._get_domain(site_url)
            # criteria: which domain set the cookie?
            if operator_func(top_domain, ck_domain):
                amount = data.get(top_domain, 0)
                data[top_domain] = amount + 1
        data['total_sum'] = reduce(lambda x, y: x + y, data.values())
        data['cookie_avg'] = data['total_sum'] / self.mapper.eval_successful_sites()
        return data

    #---------------------------------------------------------------------------
    # HTTP-TRAFFIC ANALYSIS
    #---------------------------------------------------------------------------
    def eval_requests(self):
        '''Evaluates number of third-party request, average and amount domains'''
        data = {}
        sites_requests = self.mapper.map_site_to_requests()
        num_requests = [len(x) for x in sites_requests.values()]
        data['total_sum'] = reduce(lambda x, y: x + y, num_requests)
        data['request_avg'] = data['total_sum'] / self.mapper.eval_successful_sites()
        return data

    def eval_domains(self):
        '''Evaluates number of third-party domains'''
        data = {}
        amount = self.mapper.eval_successful_sites()
        domains = self._get_requested_domains()
        site_requests = self.mapper.map_site_to_requests()
        for requests in site_requests.values():
            reqdoms = set([self._get_domain(req[0]) for req in requests])
            matches = [dom for dom in reqdoms if dom in domains]
            for domain in matches:
                frequency = data.get(domain, 0)
                data[domain] = frequency + 1
        # how many present on more than one site?
        frequent = [k for k, v in data.items() if v > 1]
        # how many present on more than 1% of sites?
        percentage = int(amount*0.01) if int(amount*0.01) > 0 else 1
        percent = [k for k, v in data.items() if v > percentage]
        # how many present on more than 10% of sites?
        tenpercentage = int(amount*0.1) if int(amount*0.1) > 0 else 1
        tenpercent = [k for k, v in data.items() if v > tenpercentage]
        data["domains_larger_one"] = len(frequent)
        data["domains_larger_percent"] = len(percent)
        data["domains_larger_ten"] = tenpercent
        data["total_sum"] = len(domains)
        return data

    def eval_tracker_distribution(self, blocklist):
        '''Maps Trackers exclusively to first rank they appear on.
        Gives insight regarding the question, when have I seen all trackers?'''
        data, trackers = {}, set()
        sites_rank = self.mapper.map_site_to_rank()
        sites_requests = self.mapper.map_site_to_requests()
        blocked = self._flatten_blocklist(blocklist)
        ranksorted = sorted(sites_rank.items(), key=lambda (k, v): (v, k))
        # remove sites without thiry-party
        ranksorted = [x for x in ranksorted if x[0] in sites_requests]
        # map amount of new trackers to rank
        for site, rank in ranksorted:
            domains = self._get_blocked_domains(sites_requests[site], blocked)
            matches = [dom for dom in domains if dom not in trackers]
            data[rank] = len(matches)
            trackers.update(matches)
        return data

    def eval_tracking_context(self, blocklist):
        '''Classifiyes third partys as trackers based on given blocking list (json)
        maps sites to amount of domains (NOT resources) that would have been blocked'''
        data, uniquedoms = {}, set()
        sites_requests = self.mapper.map_site_to_requests()
        blocked = self._flatten_blocklist(blocklist)
        # check all blocked domains that occur in site request urls
        for site, requests in sites_requests.items():
            matches = self._get_blocked_domains(requests, blocked)
            data[site] = len(matches)
            uniquedoms.update(matches)
        # calc total sum, unique trackers and avg per site
        data["total_sum"] = reduce(lambda x, y: x + y, data.values())
        data["unique_trackers"] = list(uniquedoms)
        data["tracker_avg"] = data["total_sum"] / self.mapper.eval_successful_sites()
        return data

    def eval_response_traffic(self):
        '''Evaluates amount of received bytes based on content length
        field in response headers'''
        data = {}
        sites_responses = self.mapper.map_site_to_responses()
        for site, responses in sites_responses.items():
            headers = [ast.literal_eval(tup[1]) for tup in responses]
            fields = [y for x in headers for y in x if y[0] == "Content-Length"]
            clengths = [x[1] for x in fields if len(x) == 2 and x[1].isdigit()]
            if len(clengths) > 0:
                data[site] = reduce(lambda x, y: int(x) + int(y), clengths)
        # calc total sum and average
        data['total_sum'] = reduce(lambda x, y: int(x) + int(y), data.values())
        data['byte_avg'] = data['total_sum'] / self.mapper.eval_successful_sites()
        # convert to kB
        data['total_sum'] = str(data['total_sum']/1000) + "kB"
        data['byte_avg'] = str(data['byte_avg']/1000) + "kB"
        return data

    def calc_pageload(self):
        '''Calculates pageload time (in milliseconds) according to timestamp between initial
        request to last response websites Note: Failed sites of the crawl are ignored'''
        data, site_reqstamps, site_respstamps, total_sum = {}, {}, {}, 0
        failed = self.mapper.eval_failed_sites()
        # map request timestamps
        for site, timestamp in self.mapper.get_request_timestamps():
            if site not in failed:
                site_reqstamps.setdefault(site, []).append(timestamp)
        # map response timestamps
        for site, timestamp in self.mapper.get_response_timestamps():
            if site not in failed:
                site_respstamps.setdefault(site, []).append(timestamp)
        # calc time difference first request, last response
        for site in site_respstamps:
            min_req = min(site_reqstamps[site])
            max_resp = max(site_respstamps[site])
            data[site] = self._calc_request_timediff(min_req, max_resp)
            total_sum += data[site]
        data["loadtime_avg"] = total_sum / self.mapper.eval_successful_sites()
        return data

    def detect_cookie_syncing(self):
        '''Detects cookie syncing behaviour in http traffic logs
           Approach: A 1-million-site Measurement and Analysis'''
        data = {}
        site_cookies = self.mapper.find_id_cookies()
        site_requests = self.mapper.map_site_to_requests()
        for site, cookies in site_cookies.items():
            #are ids leaked in requested third party urls or referers?
            requests = site_requests.get(site, [])
            urls = [tpl[0] for tpl in requests] + list(set([tpl[2] for tpl in requests]))
            cvalues = [tpl[1] for tpl in cookies]
            matches = [url for url in urls if len([x for x in cvalues if x in url]) > 0]
            data[site] = list(set([self._get_domain(x) for x in matches]))
        # total amount of sites leaking cookie ids
        data['total_sum'] = len([x for x in data.values() if len(x) > 0])
        data['site_percentage'] = float(data['total_sum']) / float(self.mapper.eval_successful_sites())
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

    def rank_third_party_requests(self, amount=10):
        '''Rank third-party domains based in crawl data (dascending)
           Which domain receives the most amount of requests?'''
        data = {}
        site_requests = self.mapper.map_site_to_requests()
        for reqtpl in site_requests.values():
            reqdomains = [self._get_domain(tpl[0]) for tpl in reqtpl]
            for domain in reqdomains:
                frequency = data.get(domain, 0)
                data[domain] = frequency + 1
        return sorted(data.items(), key=lambda (k, v): v, reverse=True)[:amount]

    def rank_third_party_prominence(self, amount=10):
        '''Ranks third-party domains based on suggested prominence metric
           Approach: A 1-million-site Measurement and Analysis'''
        data = {}
        sites_rank = self.mapper.map_site_to_rank()
        sites_requests = self.mapper.map_site_to_requests()
        domains = self._get_requested_domains()
        for site, requests in sites_requests.items():
            reqdoms = set([self._get_domain(req[0]) for req in requests])
            matches = [dom for dom in reqdoms if dom in domains]
            for domain in matches:
                # prominence: sum of all 1/rank(site) where domain is present
                prominence = data.get(domain, 0)
                data[domain] = prominence + 1.0/sites_rank[site]
        return sorted(data.items(), key=lambda (k, v): v, reverse=True)[:amount]

    def rank_third_party_sites(self, amount=10):
        '''Rank third-party domains based in crawl data (descending)
           Which domain occures on the most distinct websites?'''
        data = {}
        site_requests = self.mapper.map_site_to_requests()
        for requests in site_requests.values():
            reqdoms = set([self._get_domain(req[0]) for req in requests])
            for domain in reqdoms:
                frequency = data.get(domain, 0)
                data[domain] = frequency + 1
        # calc percentage, put in perspective with failed sites
        data = self._calc_rel_percentage(data)
        return sorted(data.items(), key=lambda (k, v): v[0], reverse=True)[:amount]

    def rank_organisation_reach(self, disconnect_dict, amount=10):
        '''Ranks the reach of an organisation based on the disconnect blocking
           list which contains organisations with their associated domains.
           Which organisation is requested the most?
           Approach: Tracking the Trackers'''
        data = {}
        org_domains = self._map_org_to_domains(disconnect_dict)
        org_orgurl = self._map_org_to_orgurl(disconnect_dict)
        reqdoms = self._get_requested_domains()
        site_requests = self.mapper.map_site_to_requests()
        # filter orgnames present in crawl to reduce overhead
        _ = org_orgurl.items()
        crawlorgs = [org for org, url in _ if self._get_domain(url) in reqdoms]
        for requests in site_requests.values():
            reqs = set([self._get_domain(tup[0]) for tup in requests])
            for org in crawlorgs:
                matches = [req for req in reqs if req in org_domains[org]]
                if len(matches) > 0:
                    frequency = data.get(org, 0)
                    data[org] = frequency + 1
        # calc percentage, put in perspective with failed sites
        data = self._calc_rel_percentage(data)
        return sorted(data.items(), key=lambda (k, v): v[0], reverse=True)[:amount]

    def _get_blocked_domains(self, requests, blocklist):
        '''Matches requests against blocklist, returning matches'''
        requrls = set([self._get_domain(tup[0]) for tup in requests])
        return [url for url in requrls if url in blocklist]

    def _get_requested_domains(self):
        '''Fetches all requested unique top domains during crawl'''
        urls = self.mapper.get_request_urls()
        # x[0] -> tuple is returned from query
        return list(set([self._get_domain(x[0]) for x in urls]))

    def _flatten_blocklist(self, nestedlist):
        '''Flattens disconnect blocklist to domain list'''
        categorie_domains = self._map_category_to_domains(nestedlist)
        return [domain for l in categorie_domains.values() for domain in l]

    def _calc_rel_percentage(self, domain_frequency):
        '''Calculates percentage based on actual crawled sites for domain
           frequency'''
        data = {}
        for domain, frequency in domain_frequency.items():
            relpercent = float(frequency) / float(self.mapper.eval_successful_sites())
            data[domain] = (frequency, relpercent)
        return data

    def _prepare_detection_data(self):
        '''Prepares dict to check for stable user identifiers
           Users are represented by dicts in lists where site is mapped to a list
           containing a dict per visit, containing requests and extracted http pairs'''
        userdata = []
        # fetch request urls per user per visit
        for userid in self.mapper.get_userids():
            sitedata = {}
            for visitid in self.mapper.get_visitids(userid):
                requests, site, visitdata = set(), "", {}
                for site_url, url, referrer in self.mapper.get_visitdata(userid, visitid):
                    site = site_url
                    requests.update([url, referrer])
                visitdata['urls'] = requests
                # extract keys and values
                visitdata['extracted'] = self._extract_http_pairs(list(requests))
                sitedata.setdefault(site, []).append(visitdata)
            userdata.append(sitedata)
        return userdata

    def _is_domain_present(self, domain, requests):
        '''Checks whether given third party is present in the given request
        requests of the site'''
        req_domains = set([self._get_domain(req[0]) for req in requests])
        return True if domain in req_domains else False

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
    def _calc_request_timediff(req_timestmp, res_timestmp):
        '''Calculates the time difference between to timestamps in milliseconds (ms)'''
        stmp_format = '%Y-%m-%dT%H:%M:%S.%fZ'
        req = datetime.datetime.strptime(req_timestmp, stmp_format)
        resp = datetime.datetime.strptime(res_timestmp, stmp_format)
        delta = resp - req
        return delta.seconds*1000 + delta.microseconds/1000

    #---------------------------------------------------------------------------
    # FINGERPRINTING ANALYSIS
    #---------------------------------------------------------------------------
    def eval_fingerprint_scripts(self, blacklist):
        '''Matches found js-scripts against blacklist'''
        data = {}
        site_scripts = self.mapper.map_site_to_js() # {site: [script...]}
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
        data["site_percentage"] = float(len(unique_sites)) / float(self.mapper.eval_successful_sites())
        return data

    def eval_fingerprint_distribution(self, blacklist):
        '''Evaluates the distribution of fingerprinting scripts based on the rank
        they appeared on'''
        data = {}
        sites_rank = self.mapper.map_site_to_rank()
        site_scripts = self.mapper.map_site_to_js()
        flatblacklist = [x for l in blacklist.values() for x in l]
        canvasscripts = self.detect_canvas_fingerprinting()
        fontscripts = self.detect_font_fingerprinting()
        # combine all scripts for general blacklist (domain, scriptname)
        resources = flatblacklist + canvasscripts + fontscripts
        scripts = [(self._get_domain(x), self._get_resource_name(x)) for x in resources]
        # evalaute which sites embed scripts and map to rank
        for site, sitejs in site_scripts.items():
            sitejs = [(self._get_domain(x), self._get_resource_name(x)) for x in sitejs]
            matches = set([tpl for tpl in sitejs if tpl in scripts])
            data[sites_rank[site]] = len(matches)
        return data

    def detect_canvas_fingerprinting(self):
        '''Detects scripts showing canvas fingerprinting behaviour
           Approach: A 1-million-site Measurement and Analysis'''
        script_symbols = self.mapper.map_js_to_symbol_canvas()
        items = script_symbols.items()
        return [js for js, sym in items if self._is_canvas_fingerprinting(sym)]

    def detect_font_fingerprinting(self):
        '''Detects scripts showing general fingerprinting (font probing) behaviour
           Approach: FPDetective: Dusting the Web for Fingerprinters'''
        script_symbols = self.mapper.map_js_to_symbol_font()
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
