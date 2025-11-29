import os
import requests


API_KEY = os.getenv('PAGESPEED_API_KEY', '')
TARGET_URL = os.getenv('PAGESPEED_TARGET_URL', 'http://127.0.0.1:5000')


def run():
    if not API_KEY:
        print('No API key')
        return
    endpoint = 'https://www.googleapis.com/pagespeedonline/v5/runPagespeed'
    params = {'url': TARGET_URL, 'key': API_KEY, 'strategy': 'desktop'}
    r = requests.get(endpoint, params=params, timeout=30)
    print(r.status_code)
    print(r.text)


if __name__ == '__main__':
    run()