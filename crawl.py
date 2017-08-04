#!/usr/bin/python
# -*- coding: utf-8 -*-
'''Starts crawls executing defined workload for measurement'''
import argparse
from crawler import AnalysisCrawler, DetectionCrawler, LoginCrawler

# constants
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
    '''init argument parser'''
    parser = argparse.ArgumentParser(description='''Crawl sites following
    different behaviour and collecting various data.''')
    parser.add_argument('browserparams',
                        metavar='browserparam', type=str, help='json file for browser config')
    parser.add_argument('managerparams',
                        metavar='managerparam', type=str, help='json file for manager config')
    parser.add_argument('sites',
                        metavar='sites', type=str, help='site input file (alexa format)')
    hlp = 'crawl type (analysis, detection, login)'
    parser.add_argument('crawltype',
                        metavar='crawltype', type=str, help=hlp)
    hlp = 'name of the output sqlite file, otherwise generated'
    parser.add_argument('--output',
                        metavar='output', type=str, help=hlp)
    hlp = 'log into certain site before performing crawl'
    parser.add_argument('--login',
                        metavar='login', type=str, help=hlp)
    return parser

def _main():
    '''wrapper for main functionality'''
    #browser_path, manager_path, sites_path, crawltype, db_prefix = _init()
    parser = _init()
    args = parser.parse_args()
    bpath, mpath, spath = args.browserparams, args.managerparams, args.sites
    # perform crawl
    print 'Preparing crawl...'
    crawler = _init_crawler(bpath, mpath, spath, args.crawltype, args.output)
    # better identifiable names for log and db
    print 'Crawling...'
    crawler.crawl()
    print 'Finished crawling, data written to: %s' %(crawler.get_dbname())

#main
if __name__ == "__main__":
    _main()
