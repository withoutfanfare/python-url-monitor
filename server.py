import requests
from datetime import datetime
import time
import logging

logging.basicConfig(filename='/tmp/debug.log', level=logging.DEBUG)

class Server:

    def __init__(self, name, url, timeout, max_fails, assert_string):
        self.name = name
        self.url = url
        self.timeout = timeout
        self.max_fails = max_fails
        self.assert_string = assert_string

        self.fails = 0
        self.status_code = 0
        self.status = ''
        self.last_checked = datetime.min
        self.notified_fail = False
        self.assert_pass = False



    def check_status(self):
        self.last_checked = datetime.now()

        try:
            r = requests.get(self.url, timeout=self.timeout)
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as e:
            self.status_code = 500
            self.status = str(e)
            self.fails += 1
        else:
            self.status_code = r.status_code
            if r.status_code == 200:
                if self.assert_string and self.assert_string != "":
                    if self.assert_string in r.text:
                        self.status = 'OK'
                        self.fails = 0
                        self.notified_fail = False
                        self.assert_pass = True
                    else:
                        self.status = 'Assert Failed'
                        self.fails += 1
                        self.assert_pass = False
            else:
                self.fails += 1
                self.status = 'ERROR'

        time.sleep(0.1)

        logging.info("Status: " + self.name)
        logging.info(self.status)

        return self
