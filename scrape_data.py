# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Name:         Electricity data web scrape
# Purpose:      Automatically scrape hourly electricity usage data from the web
#
# Author:       james.scouller
#
# Created:      28/10/2021
# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# global imports
import os
import re
import math
import time
import functools
import traceback
import sys
import pandas as pd
from environs import Env
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# custom module imports
# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# main code

# make sure geoDriver starts hidden
flag = 0x08000000  # No-Window flag
# flag = 0x00000008  # Detached-Process flag, if first doesn't work
webdriver.common.service.subprocess.Popen = functools.partial(webdriver.common.service.subprocess.Popen, creationflags=flag)

def print_indent(msg, n=1):
    '''
    Wrapper to do indented printing
    '''
    print('\t'*n, msg)

def error_catcher(func):
    '''
    Error catcher decorator to handle closing down browser properly if an error is encountered
    '''
    def run_and_catch(*args, **kwargs):
        try:
            error_caused = False
            return func(*args, **kwargs)
        except TimeoutException:
            error_caused = True
            print_indent('{} method timed out waiting for an element!'.format(func.__name__))
            exc_type, exc_value, exc_tb = sys.exc_info()
            print_indent(exc_value.msg, 2)
        except Exception:
            error_caused = True
            print_indent('{} method caused an unexpected error!'.format(func.__name__))
            traceback.print_exc()
        finally:
            if error_caused:
                args[0].driver.close()

    return run_and_catch

@error_catcher
class AutoBrowser(object):
    '''
    Selenium driven instance of Firefox for automatically navigating webpages to scrape data

    :param env_filepath: Optional input specifying location of environment file with urls and login info
    :param timeout: Optional input specifying length of time to wait for element to appear in seconds
    :returns: None
    :raises TimeoutException: Raised when a target element does not appear after the configured timeout
    '''

    def __init__(self, env_filepath=None, timeout=3):
        # working dir
        self.working_dir = os.path.dirname(__file__)
        print('Starting Firefox...')
        self.driver = webdriver.Firefox()
        # hide window off-screen if desired
        # driver.set_window_position(-10000, 0)
        # setup a waiter helper
        self.timeout = timeout
        self.wait = WebDriverWait(self.driver, self.timeout)
        # get data from env file
        env_filepath = env_filepath if env_filepath else os.path.join(self.working_dir, '.env')
        Env().read_env(env_filepath)
        # assume env file contains a login url and a second url that points towards page to scrape data from
        self.login_url = os.getenv('LOGIN_URL', 'https://www.google.com')
        self.data_url = os.getenv('DATA_URL', 'https://www.google.com')
        # assume env file contains login credentials
        self.username = os.getenv('USERNAME', 'username')
        self.password = os.getenv('PASSWORD', '1234')

        print('Initialised {}!'.format(self.__class__.__name__))

    @error_catcher
    def login(self):
        # go to login page and wait for login button to appear
        print('Loading login page...')
        self.driver.get(self.login_url)
        target_id = 'loginButton'
        elem_login_btn = self.wait.until(EC.element_to_be_clickable((By.ID, target_id)), 'element with id={} was not clickable within {}s'.format(target_id, self.timeout))
        elem_username = self.driver.find_element_by_id('userName')
        elem_password = self.driver.find_element_by_id('userPassword')
        elem_username.send_keys(self.username)
        elem_password.send_keys(self.password)
        elem_login_btn.click()
        print('Logging in...')


browser = AutoBrowser()
browser.login()
