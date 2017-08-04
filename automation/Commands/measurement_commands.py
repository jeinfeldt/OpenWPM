#!/usr/bin/python
# -*- coding: utf-8 -*-
'''Implementations regarding new commands for measurement: login to social media'''
from selenium.common.exceptions import NoSuchElementException
from utils.webdriver_extensions import wait_and_find

def login(webdriver, logindata):
    '''Login to page with data provided in loginconfig'''
    print "Login in whoop whoop"
    print logindata
    mailfield = webdriver.find_element_by_id('email')
    print mailfield
