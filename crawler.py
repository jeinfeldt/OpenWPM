#!/usr/bin/python
# -*- coding: utf-8 -*-
'''Implementations regarding concrete crawlers and util functions'''
import json
import os
from time import gmtime, strftime
from automation import TaskManager, CommandSequence

class DataCrawler(object):
    '''High level class encapsulating crawling util functions'''

    def __init__(self, browser_param_path, manager_param_path, site_input):
        # read parameters
        self.browserpar = self._load_parameters(browser_param_path)
        self.managerpar = self._load_parameters(manager_param_path)
        self.sites = self.load_websites(site_input)

    def crawl(self):
        '''Abstract method to be overwritten by subclasses'''
        pass

    def get_dbname(self):
        ''' Gets the generated output dbname '''
        return self.managerpar['database_name']

    def _set_dbname(self, db_prefix, browser_param_path, crawltype):
        '''Adjusts database output name based on crawltype'''
        gen_prefix = self.generate_crawl_prefix(browser_param_path, crawltype, len(self.sites))
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
    def load_websites(file_path):
        '''loads defined amount of pages from alexa file, websites are returned
           in format http://www.[domainname].[identifier]'''
        url_format = 'http://www.%s'
        with open(file_path, 'r') as data:
            sites = [line.strip() for line in data if "#" not in line]
            sites = [url_format %(line) for line in sites if line] # remove blank
            return [x.lower() for x in sites]

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
    def __init__(self, browser_param_path, manager_param_path, site_input, db_prefix=None):
        super(AnalysisCrawler, self).__init__(browser_param_path, manager_param_path, site_input)
        self._set_dbname(db_prefix, browser_param_path, self.CRAWL_TYPE)

    def crawl(self):
        '''Runs a crawl to measure various metrics regarding third-party tracking'''
        manager = TaskManager.TaskManager(self.managerpar, [self.browserpar])
        for site in self.sites:
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
    def __init__(self, browser_param_path, manager_param_path, site_input, db_prefix=None):
        super(DetectionCrawler, self).__init__(browser_param_path, manager_param_path, site_input)
        self._set_dbname(db_prefix, browser_param_path, self.CRAWL_TYPE)

    def crawl(self):
        '''Runs crawl resulting in dataset for unsupervised tracking detection'''
        self.browserpar['disable_flash'] = True
        for _ in range(0, self.NUM_USERS):
            manager = TaskManager.TaskManager(self.managerpar, [self.browserpar])
            for site in self.sites:
                for _ in range(0, self.NUM_VISITS):
                    command_sequence = CommandSequence.CommandSequence(site)
                    command_sequence.get(sleep=15, timeout=30)
                    manager.execute_command_sequence(command_sequence, index='**')
            manager.close()

class LoginCrawler(DataCrawler):
    '''Crawler enabling login behavior for certain sites'''

    # constants
    CRAWL_TYPE = "login"

    # behaviour
    def __init__(self, browser_param_path, manager_param_path, site_input, db_prefix=None):
        super(LoginCrawler, self).__init__(browser_param_path, manager_param_path, site_input)
        self._set_dbname(db_prefix, browser_param_path, self.CRAWL_TYPE)

    def crawl(self):
        pass
