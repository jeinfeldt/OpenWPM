#!/usr/bin/python
# -*- coding: utf-8 -*-
'''Starts crawls executing defined workload for measurement'''
import sys, json, os
from time import gmtime, strftime
from automation import TaskManager, CommandSequence

# constants
WEBSITE_FILE = 'measurement/assets/quantcast-top-million.txt'
HELP = '''Scripts needs to be executed with the following parameters:
1. path to browser parameter .json-file\n2. path to manager parameter .json-file
3. number of pages to crawl\nHint: For better results perform script as sudo'''

# public
def crawl(sites, browser_params, manager_params):
    '''crawls given sites with given parameters'''
    # Shuts down the browsers and waits for the data to finish logging
    crawl_type = manager_params['crawl_type']
    func = _crawl_analysis if crawl_type == "analysis" else _crawl_detection
    func(sites, browser_params, manager_params)

def _crawl_analysis(sites, browser_params, manager_params):
    '''Runs a crawl to measure various metrics regarding third-party tracking'''
    manager = TaskManager.TaskManager(manager_params, [browser_params])
    for site in sites:
        command_sequence = CommandSequence.CommandSequence(site)
        # Start by visiting the page
        command_sequence.get(sleep=0, timeout=60)
        # dump_profile_cookies/dump_flash_cookies closes the current tab.
        command_sequence.dump_profile_cookies(60)
        command_sequence.dump_flash_cookies(60)
        manager.execute_command_sequence(command_sequence, index='**')
    manager.close()

def _crawl_detection(sites, browser_params, manager_params):
    '''Runs crawl resulting in dataset for unsupervised tracking detection'''
    num_visits, num_users = manager_params['num_visits'], manager_params['num_users']
    browser_params['disable_flash'] = True
    # TODO: just for testing
    manager_params['database_name'] = "05-vanilla-100-detection-crawl-data.sqlite"
    manager = TaskManager.TaskManager(manager_params, [browser_params])
    for site in sites:
        for _ in range(0, num_visits):
            command_sequence = CommandSequence.CommandSequence(site)
            command_sequence.get(sleep=0, timeout=60)
            manager.execute_command_sequence(command_sequence, index='**')
    manager.close()

def load_websites(file_path, amount):
    '''loads defined amount of pages from file, websites are returned
       in format http://www.[domainname].[identifier]
       Currently only for quantcast files'''
    url_format = 'http://www.%s'
    filter_string = 'Hidden profile'
    with open(file_path, 'r') as data:
        # specific parsing to quantcast format
        sites = [row.strip() for row in list(data) if row[0].isdigit()]
        sites = [row for row in sites if filter_string not in row]
        sites = [url_format %(row.split("\t")[1]) for row in sites]
        return sites[:amount]

def load_parameters(file_path):
    '''loads crawl parameters from .json file'''
    with open(file_path, 'r') as data:
        return json.load(data)

def generate_crawl_prefix(browser_params_path, manager_params, amount):
    '''adjusts parameters for manager suitable for measurement'''
    tmp = '%s-%s-%s-%s-'
    timestamp = strftime("%d%m%y-%H:%M", gmtime())
    prefix = os.path.basename(browser_params_path).split('_')[0]
    return tmp %(timestamp, prefix, str(amount), manager_params['crawl_type'])

def _init():
    '''guard clause and init for script'''
    args = sys.argv[1:]
    if len(args) != 3:
        print HELP
        sys.exit()
    return args

def _main():
    '''wrapper for main functionality'''
    browser_path, manager_path, amount = _init()
    # perform crawl
    print 'Preparing crawl...'
    browser_params = load_parameters(browser_path)
    manager_params = load_parameters(manager_path)
    # better identifiable names for log and db
    prefix = generate_crawl_prefix(browser_path, manager_params, amount)
    manager_params['database_name'] = prefix + manager_params['database_name']
    manager_params['log_file'] = prefix + manager_params['log_file']
    websites = load_websites(WEBSITE_FILE, int(amount))
    print 'Crawling...'
    crawl(websites, browser_params, manager_params)
    print 'Finished crawling, data written to: %s' %(manager_params['database_name'])

#main
if __name__ == "__main__":
    _main()
