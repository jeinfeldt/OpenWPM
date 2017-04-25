#!/usr/bin/python
# -*- coding: utf-8 -*-
'''Starts crawls executing defined workload for measurement'''
import sys, json, os
from automation import TaskManager, CommandSequence

# constants
WEBSITE_FILE = 'measurement/quantcast-top-million.txt'
HELP = '''Scripts needs to be executed with the following parameters:
1. path to browser parameter .json-file\n2. path to manager parameter .json-file
3. number of pages to crawl\nHint: For better results perform script as sudo'''

# public
def crawl(sites, browser_params, manager_params):
    '''crawls given sites with given parameters'''
    manager = TaskManager.TaskManager(manager_params, [browser_params])
    sites = ["http://www.spiegel.de"]
    for site in sites:
        command_sequence = CommandSequence.CommandSequence(site)
        # Start by visiting the page
        command_sequence.get(sleep=0, timeout=120)
        # dump_profile_cookies/dump_flash_cookies closes the current tab.
        command_sequence.dump_profile_cookies(120)
        #command_sequence.dump_flash_cookies(120)
        manager.execute_command_sequence(command_sequence, index='**')
    # Shuts down the browsers and waits for the data to finish logging
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

def generate_db_name(browser_params_path, amount):
    '''adjusts parameters for manager suitable for measurement'''
    db_name = '%s-%s-crawl-data.sqlite'
    prefix = os.path.basename(browser_params_path).split('_')[0]
    return db_name %(prefix, str(amount))

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
    db_name = generate_db_name(browser_path, amount)
    manager_params['database_name'] = db_name
    websites = load_websites(WEBSITE_FILE, int(amount))
    print 'Crawling...'
    crawl(websites, browser_params, manager_params)
    print 'Finished crawling, data written to: %s' %(db_name)

#main
if __name__ == "__main__":
    _main()
