import os
import time
import unittest
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests


BASE_URL = os.getenv('BASE_URL', 'http://127.0.0.1:5000')


def fetch(path):
    url = BASE_URL + path
    t0 = time.perf_counter()
    resp = requests.get(url, timeout=10)
    dt = time.perf_counter() - t0
    return path, resp.status_code, dt


class PerformanceTests(unittest.TestCase):
    def test_page_load_speed(self):
        paths = ['/', '/login', '/products']
        results = []
        for p in paths:
            results.append(fetch(p))
        for path, status, dt in results:
            self.assertEqual(status, 200)

    def test_load_50_parallel_users(self):
        path = '/products'
        with ThreadPoolExecutor(max_workers=50) as ex:
            futures = [ex.submit(fetch, path) for _ in range(50)]
            statuses = []
            dts = []
            for f in as_completed(futures):
                _, status, dt = f.result()
                statuses.append(status)
                dts.append(dt)
        self.assertTrue(all(s == 200 for s in statuses))


if __name__ == '__main__':
    unittest.main()