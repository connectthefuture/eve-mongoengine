
import uuid
import unittest
from operator import attrgetter
from eve_mongoengine import EveMongoengine
from tests import (BaseTest, Eve, SimpleDoc, ComplexDoc, Inner, LimitedDoc,
                   WrongDoc, SETTINGS)

class TestHttpGet(BaseTest, unittest.TestCase):

    def test_find_one(self):
        d = SimpleDoc(a='Tom', b=223).save()
        response = self.client.get('/simpledoc/%s' % d.id)
        # has to return one record
        json_data = response.get_json()
        self.assertIn('updated', json_data)
        self.assertIn('created', json_data)
        self.assertEqual(json_data['_id'], str(d.id))
        self.assertEqual(json_data['a'], 'Tom')
        self.assertEqual(json_data['b'], 223)
        d.delete()

    def test_find_one_projection(self):
        # XXX: this it not eve's standard!
        self.skipTest('Projection on one document not supported')
        d = SimpleDoc(a='Tom', b=223).save()
        response = self.client.get('/simpledoc/%s?projection={"a":1}' % d.id)
        # has to return one record
        json_data = response.get_json()
        self.assertIn('updated', json_data)
        self.assertIn('created', json_data)
        self.assertNotIn('b', json_data)
        self.assertEqual(json_data['_id'], str(d.id))
        self.assertEqual(json_data['a'], 'Tom')
        d.delete()

    def test_find_one_nonexisting(self):
        response = self.client.get('/simpledoc/abcdef')
        self.assertEqual(response.status_code, 404)
        

    def test_find_all(self):
        _all = []
        for data in ({'a': "Hello", 'b':1},
                     {'a': "Hi", 'b': 2},
                     {'a': "Seeya", 'b': 3}):
            d = SimpleDoc(**data).save()
            _all.append(d)
        response = self.client.get('/simpledoc')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        s = set([item['a'] for item in data['_items']])
        self.assertSetEqual(set(['Hello', 'Hi', 'Seeya']), s)
        # delete records
        for d in _all:
            d.delete()

    def test_find_all_projection(self):
        d = SimpleDoc(a='Tom', b=223).save()
        response = self.client.get('/simpledoc?projection={"a": 1}')
        self.assertNotIn('b', response.get_json()['_items'][0])
        response = self.client.get('/simpledoc?projection={"a": 1, "b": 1}')
        data = response.get_json()['_items'][0]
        self.assertIn('b', data)
        self.assertIn('a', data)
        d.delete()

    def test_find_all_pagination(self):
        self.skipTest("Not implemented yet.")

    def test_find_all_sorting(self):
        d = SimpleDoc(a='abz', b=3).save()
        d2 = SimpleDoc(a='abc', b=-7).save()
        response = self.client.get('/simpledoc?sort={"a":1}')
        json_data = response.get_json()
        real = map(lambda x: x['a'], json_data['_items'])
        expected = [u'abc', u'abz']
        self.assertListEqual(real, expected)

        response = self.client.get('/simpledoc?sort={"b":-1}')
        json_data = response.get_json()
        real = map(lambda x: x['b'], json_data['_items'])
        expected = [3, -7]
        self.assertListEqual(real, expected)
        d.delete()
        d2.delete()

    def test_find_all_filtering(self):
        d = SimpleDoc(a='x', b=987).save()
        d2 = SimpleDoc(a='y', b=123).save()
        response = self.client.get('/simpledoc?where={"a": "y"}')
        json_data = response.get_json()
        try:
            self.assertEqual(len(json_data['_items']), 1)
            self.assertEqual(json_data['_items'][0]['b'], 123)
        finally:
            d.delete()
            d2.delete()

    def test_embedded_resource_serialization(self):
        s = SimpleDoc(a="Answer to everything", b=42).save()
        d = ComplexDoc(r=s).save()
        response = self.client.get('/complexdoc?embedded={"r":1}')
        json_data = response.get_json()
        expected = {'a': "Answer to everything", 'b': 42}
        try:
            emb = json_data['_items'][0]['r']
            self.assertEqual(emb['a'], expected['a'])
            self.assertEqual(emb['b'], expected['b'])
            self.assertIn('created', emb)
            self.assertIn('updated', emb)
        finally:
            d.delete()
            s.delete()

    def test_uppercase_resource_names(self):
        # test default lowercase
        response = self.client.get('/SimpleDoc')
        self.assertEqual(response.status_code, 404)
        # uppercase
        ext = EveMongoengine()
        settings = ext.create_settings([SimpleDoc], lowercase=False)
        settings.update(SETTINGS)
        app = Eve(settings=settings)
        ext.init_app(app)
        client = app.test_client()
        d = SimpleDoc(a='Tom', b=223).save()
        response = client.get('/SimpleDoc/')
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        expected_url = json_data['_links']['self']['href']
        if ':' in expected_url:
            expected_url = '/' + '/'.join( expected_url.split('/')[1:] )
        self.assertEqual(expected_url, '/SimpleDoc')
        # not lowercase when uppercase
        response = client.get('/simpledoc/')
        self.assertEqual(response.status_code, 404)
