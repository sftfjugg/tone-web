"""
# schedule.every(1).seconds.do(job)
# schedule.every().hour.do(job)
# schedule.every().day.at("10:30").do(job)
# schedule.every(5).to(10).days.do(job)
# schedule.every().monday.do(job)
# schedule.every().wednesday.at("13:15").do(job)
"""
import logging
import sys
import time
from datetime import datetime

import requests
import schedule


def sync_case_to_cache_job():
    sync_url = '{}/api/case/sync_case_to_cache/'.format(sys.argv[1])
    try:
        resp = requests.get(sync_url, verify=False)
        success = True if resp.json()['code'] == 200 else False
        data = resp.json()['data']
    except Exception as e:
        success = False
        data = None
        logging.error('sync_case_to_cache failed. error detail:{}', str(e))
    logging.info('sync_case_to_cache schedule. time:{}, success:{}, detail:{}\n'.format(datetime.now(), success, data))


schedule.every(3).minutes.do(sync_case_to_cache_job)


while True:
    schedule.run_pending()
    time.sleep(1)
