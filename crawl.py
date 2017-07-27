#!/usr/bin/python
# -*- coding: utf-8 -*-
'''Starts crawls executing defined workload for measurement'''
import sys
from crawler import AnalysisCrawler, DetectionCrawler, LoginCrawler

# constants
HELP = '''\nScripts needs to be executed with the following parameters:
1. path to browser parameter .json-file\n2. path to manager parameter .json-file
3. site input file (alexa list)
4. Crawl type (analysis, detection, login)\n(5. Prefix of output db)
Hint: For better results perform script as sudo\n'''
CRAWLTYPE_ERROR = "Crawltype unknown! Use analysis, detection, login"

def _init_crawler(browser_path, manager_path, sites_path, crawltype, db_prefix):
    '''crawls given sites with given parameters'''
    if crawltype == 'analysis':
        return AnalysisCrawler(browser_path, manager_path, sites_path, db_prefix)
    elif crawltype == 'detection':
        return DetectionCrawler(browser_path, manager_path, sites_path, db_prefix)
    elif crawltype == 'login':
        return LoginCrawler(browser_path, manager_path, sites_path, db_prefix)
    else:
        raise ValueError(CRAWLTYPE_ERROR)

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
    browser_path, manager_path, sites_path, crawltype, db_prefix = _init()
    # perform crawl
    print 'Preparing crawl...'
    crawler = _init_crawler(browser_path, manager_path, sites_path, crawltype, db_prefix)
    # better identifiable names for log and db
    print 'Crawling...'
    crawler.crawl()
    print 'Finished crawling, data written to: %s' %(crawler.get_dbname())

#main
if __name__ == "__main__":
    _main()
