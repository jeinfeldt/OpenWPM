#!/usr/bin/python
# -*- coding: utf-8 -*-
'''Implementations regarding concrete crawlers and util functions'''
import json
import os
from time import gmtime, strftime
from automation import TaskManager, CommandSequence

class DataCrawler(object):
    '''High level class encapsulating crawling util functions'''

    def __init__(self, browser_param_path, manager_param_path):
        # read parameters
        self.bpath = browser_param_path
        self.mpath = manager_param_path
        self.browserpar = self._load_parameters(self.bpath)
        self.managerpar = self._load_parameters(self.mpath)

    def crawl(self, sites):
        '''Abstract method to be overwritten by subclasses'''
        pass

    def get_dbname(self):
        ''' Gets the generated output dbname '''
        return self.managerpar['database_name']

    def _set_dbname(self, sites, db_prefix, browser_param_path, crawltype):
        '''Adjusts database output name based on crawltype'''
        gen_prefix = self.generate_crawl_prefix(browser_param_path, crawltype, len(sites))
        prefix = db_prefix if db_prefix is not None else gen_prefix
        self.managerpar['database_name'] = prefix + self.managerpar['database_name']
        self.managerpar['log_file'] = prefix + self.managerpar['log_file']

    @staticmethod
    def generate_crawl_prefix(browser_params_path, crawltype, amount):
        '''adjusts parameters for manager suitable for measurement'''
        tmp = '%s-%s-%s-%s-'
        timestamp = strftime("%Y%m%d-%H:%M", gmtime())
        prefix = os.path.basename(browser_params_path).split('_')[0]
        return tmp %(timestamp, prefix, str(amount), crawltype)

    @staticmethod
    def _load_parameters(file_path):
        '''loads crawl parameters from .json file'''
        with open(file_path, 'r') as data:
            return json.load(data)

class AnalysisCrawler(DataCrawler):
    '''Crawler generating standard data (storage, http data, javascript)'''

    # constants
    CRAWL_TYPE = "analysis"

    # behaviour
    def __init__(self, browser_param_path, manager_param_path, db_prefix=None):
        super(AnalysisCrawler, self).__init__(browser_param_path, manager_param_path)
        self.db_prefix = db_prefix

    def crawl(self, sites):
        '''Runs a crawl to measure various metrics regarding third-party tracking.
           Sites are expected as list including protocol, e.g. http://www.hdm-stuttgart.de'''
        self._set_dbname(sites, self.db_prefix, self.bpath, self.CRAWL_TYPE)
        manager = TaskManager.TaskManager(self.managerpar, [self.browserpar])
        for site in sites:
            # we run a stateless crawl (fresh profile for each page)
            command_sequence = CommandSequence.CommandSequence(site, reset=True)
            # Start by visiting the page
            command_sequence.get(sleep=15, timeout=30)
            # dump_profile_cookies/dump_flash_cookies closes the current tab.
            command_sequence.dump_profile_cookies(120)
            command_sequence.dump_flash_cookies(120)
            manager.execute_command_sequence(command_sequence, index='**')
        manager.close()

class DetectionCrawler(DataCrawler):
    '''Crawler generating data for detection algorithm
       Approach: Unsupervised Detection of Web Trackers '''

    # constants
    CRAWL_TYPE = "detection"
    NUM_USERS = 3
    NUM_VISITS = 3

    # behaviour
    def __init__(self, browser_param_path, manager_param_path, db_prefix=None):
        super(DetectionCrawler, self).__init__(browser_param_path, manager_param_path)
        self.db_prefix = db_prefix

    def crawl(self, sites):
        '''Runs crawl resulting in dataset for unsupervised tracking detection
        Sites are expected as list including protocol, e.g. http://www.hdm-stuttgart.de'''
        self._set_dbname(sites, self.db_prefix, self.bpath, self.CRAWL_TYPE)
        self.browserpar['disable_flash'] = True
        for _ in range(0, self.NUM_USERS):
            manager = TaskManager.TaskManager(self.managerpar, [self.browserpar])
            for site in sites:
                for _ in range(0, self.NUM_VISITS):
                    command_sequence = CommandSequence.CommandSequence(site)
                    command_sequence.get(sleep=15, timeout=30)
                    manager.execute_command_sequence(command_sequence, index='**')
            manager.close()

class LoginCrawler(DataCrawler):
    '''Crawler enabling login behavior for certain sites. One can either crawl:
      statefull: login to certain site and crawl others
      stateless: crawl different login sites and log results'''

    # constants
    CRAWL_TYPE = "login"
    LOGIN_PARAMS_PATH = "params/login_params.json"

    # behaviour
    def __init__(self, browser_param_path, manager_param_path, db_prefix=None):
        super(LoginCrawler, self).__init__(browser_param_path, manager_param_path)
        self.db_prefix = db_prefix
        self.loginpar = self._load_parameters(self.LOGIN_PARAMS_PATH)

    def crawl(self, sites):
        '''Log in to site with given params (constants), dump cookies and flash'''
        self._set_dbname(sites, self.db_prefix, self.bpath, self.CRAWL_TYPE)
        manager = TaskManager.TaskManager(self.managerpar, [self.browserpar])
        for site in sites:
            params = self._fetch_params(site)
            commandseq = CommandSequence.CommandSequence(site)
            commandseq.get(sleep=15, timeout=30)
            commandseq.login(logindata=params, timeout=30)
            manager.execute_command_sequence(commandseq, index='**')
        manager.close()

    def _fetch_params(self, site):
        '''Fetch corresponding login params for given site'''
        key = [key for key in self.loginpar.keys() if key in site][0]
        par = self.loginpar[key]
        return (par['emailid'], par['passid'], par['email'], par['password'], par['submitid'])
