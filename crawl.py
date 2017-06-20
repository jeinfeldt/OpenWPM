#!/usr/bin/python
# -*- coding: utf-8 -*-
'''Starts crawls executing defined workload for measurement'''
import sys, json, os
from time import gmtime, strftime
from automation import TaskManager, CommandSequence

# constants
HELP = '''\nScripts needs to be executed with the following parameters:
1. path to browser parameter .json-file\n2. path to manager parameter .json-file
3. number of pages to crawl\n4. site input file (alexa list)
(5. Prefix of output db)\nHint: For better results perform script as sudo\n'''

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
        # we run a stateless crawl (fresh profile for each page)
        command_sequence = CommandSequence.CommandSequence(site, reset=True)
        # Start by visiting the page
        command_sequence.get(sleep=15, timeout=30)
        # dump_profile_cookies/dump_flash_cookies closes the current tab.
        command_sequence.dump_profile_cookies(120)
        command_sequence.dump_flash_cookies(120)
        manager.execute_command_sequence(command_sequence, index='**')
    manager.close()

def _crawl_detection(sites, browser_params, manager_params):
    '''Runs crawl resulting in dataset for unsupervised tracking detection'''
    num_visits, num_users = manager_params['num_visits'], manager_params['num_users']
    browser_params['disable_flash'] = True
    for _ in range(0, num_users):
        manager = TaskManager.TaskManager(manager_params, [browser_params])
        for site in sites:
            for _ in range(0, num_visits):
                command_sequence = CommandSequence.CommandSequence(site)
                command_sequence.get(sleep=15, timeout=30)
                manager.execute_command_sequence(command_sequence, index='**')
        manager.close()

def load_websites(file_path, amount):
    '''loads defined amount of pages from alexa file, websites are returned
       in format http://www.[domainname].[identifier]'''
    url_format = 'http://www.%s'
    with open(file_path, 'r') as data:
        sites = [line.strip() for line in data if "#" not in line]
        sites = [url_format %(line) for line in sites if line] # remove blank
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
    if len(args) < 4:
        print HELP
        sys.exit()
    if len(args) == 4:
        args.append(None)
    return args

def _main():
    '''wrapper for main functionality'''
    browser_path, manager_path, amount, sites_path, db_prefix = _init()
    # perform crawl
    print 'Preparing crawl...'
    browser_params = load_parameters(browser_path)
    manager_params = load_parameters(manager_path)
    # better identifiable names for log and db
    generated = generate_crawl_prefix(browser_path, manager_params, amount)
    prefix = db_prefix if db_prefix is not None else generated
    manager_params['database_name'] = prefix + manager_params['database_name']
    manager_params['log_file'] = prefix + manager_params['log_file']
    websites = load_websites(sites_path, int(amount))
    print 'Crawling...'
    crawl(websites, browser_params, manager_params)
    print 'Finished crawling, data written to: %s' %(manager_params['database_name'])

#main
if __name__ == "__main__":
    _main()
