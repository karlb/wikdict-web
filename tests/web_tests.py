import wikdict_web
import unittest
from flask_testing import TestCase

class MyTestCase(TestCase):

    def create_app(self):
        wikdict_web.app.config['TESTING'] = True
        return wikdict_web.app

    def test_root(self):
        rv = self.client.get('/')
        self.assertEqual(rv.status_code, 200)

    def test_home(self):
        rv = self.client.get('/de-en/')
        assert rv.status_code == 200

    def test_find(self):
        rv = self.client.get('/de-en/Haus')
        assert rv.status_code == 200
        assert 'house'.encode('utf-8') in rv.data

    def test_miss(self):
        rv = self.client.get('/de-en/Problemsuchwort')
        assert rv.status_code == 200
        assert 'Sorry'.encode('utf-8') in rv.data

if __name__ == '__main__':
    unittest.main()
