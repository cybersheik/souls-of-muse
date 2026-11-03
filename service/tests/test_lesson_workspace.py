"""Real HTTP, role/meeting scopes and durable lesson state; no inference."""
import copy
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI
from fastapi.testclient import TestClient
from service.app import create_app
from service.identity import password_hash

class NoInference:
    def complete(self, *args, **kwargs):
        raise AssertionError('Lesson work must not call a model')

class LessonWorkspace(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.accounts={name:{'role':role,'password_hash':password_hash('lesson-test-only')} for name,role in [('M','maestro'),('A','artist'),('otherM','maestro'),('otherA','artist')]}
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory(prefix='cx1-lesson-test-');self.addCleanup(self.directory.cleanup)
        self.env={'SOM_WEB_ACCOUNTS':json.dumps(self.accounts),'SOM_COOKIE_SECURE':'0'}
        self.build();self.m=self.login('M');self.a=self.login('A')
        r=self.m.post('/api/harness/sessions',json={'kind':'individual','league':'string','maestro_alias':'M','artist_alias':'A','artist_id':'A','source_lang':'en','target_lang':'vi'})
        self.assertEqual(r.status_code,201,r.text);self.path='/api/harness/sessions/'+r.json()['id']
        self.doc={'revision':0,'plan':[{'title':'Warm up','duration':'3 min','goal':'Even notes','tips':['Keep the pulse']},{'title':'Play phrase','duration':'5 min','goal':'Clean changes','tips':[]}],'step':0,'notebook':{'chords':['Am','F#7'],'notation':'X:1\nM:4/4\nL:1/4\nK:C\nC D E F|','tabs':'e|--0--2--|'}}
    def build(self,on_write=None):
        app=create_app(data_dir=self.directory.name,adapter=NoInference(),environ=self.env,on_write=on_write)
        self.site=FastAPI();self.site.mount('/api/harness',app)
    def login(self,name):
        c=TestClient(self.site,headers={'Origin':'http://testserver'});self.addCleanup(c.close)
        self.assertEqual(c.post('/api/harness/auth/login',json={'username':name,'password':'lesson-test-only'}).status_code,200)
        return c
    def read(self,c=None):return (c or self.m).get(self.path+'/lesson')
    def write(self,doc=None,c=None):return (c or self.m).post(self.path+'/lesson',json=doc or self.doc)
    def test_new_meeting_starts_empty_without_sample_data(self):
        r=self.read();self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(r.json(),{'revision':0,'plan':[],'step':None,'notebook':{'chords':[],'notation':'','tabs':''}})
    def test_teacher_plan_step_and_all_notebook_views_survive_restart(self):
        r=self.write();self.assertEqual(r.status_code,200,r.text);doc=r.json();self.assertEqual(doc['revision'],1)
        doc['step']=1;r=self.write(doc);self.assertEqual(r.status_code,200,r.text);expected=r.json()
        self.assertEqual(self.read(self.a).json(),expected)
        cookies=self.a.cookies;self.build();client=TestClient(self.site,cookies=cookies);self.addCleanup(client.close)
        self.assertEqual(self.read(client).json(),expected)
        self.assertTrue(self.m.get(self.path+'/audit/verify').json()['valid'])
    def test_only_meeting_maestro_can_write_and_origin_is_checked(self):
        for name in ['otherM','otherA']:
            client=self.login(name)
            self.assertEqual(self.read(client).status_code,404)
            self.assertIn(self.write(c=client).status_code,[403,404])
        self.assertEqual(self.write(c=self.a).status_code,403)
        self.assertEqual(self.m.post(self.path+'/lesson',headers={'Origin':'https://wrong.invalid'},json=self.doc).status_code,403)
        anonymous=TestClient(self.site);self.addCleanup(anonymous.close)
        self.assertIn(anonymous.get(self.path+'/lesson').status_code,[401,503])
        self.assertEqual(self.read().json()['revision'],0)
    def test_stale_tab_cannot_overwrite_and_lost_response_replay_is_harmless(self):
        first=self.write();self.assertEqual(first.status_code,200,first.text)
        self.assertEqual(self.write().json(),first.json())
        stale=copy.deepcopy(self.doc);stale['plan'][0]['title']='Stale override'
        self.assertEqual(self.write(stale).status_code,409)
        self.assertEqual(self.read().json(),first.json())
    def test_invalid_shapes_bounds_and_current_step_are_rejected(self):
        cases=[]
        for key,value in [('step',True),('step',-1),('step',2),('revision',True),('revision',-1),('revision','0'),('unknown','x')]:
            d=copy.deepcopy(self.doc);d[key]=value;cases.append(d)
        for key,value in [('title',''),('title','x'*161),('tips',['x']*11),('bogus','x')]:
            d=copy.deepcopy(self.doc);d['plan'][0][key]=value;cases.append(d)
        d=copy.deepcopy(self.doc);d['notebook']['notation']='x'*8001;cases.append(d)
        d=copy.deepcopy(self.doc);d['notebook']['chords']=['x']*65;cases.append(d)
        for d in cases:
            with self.subTest(d=str(d)[:160]):self.assertEqual(self.write(d).status_code,422)
        self.assertEqual(self.read().json()['revision'],0)
    def test_two_tabs_have_one_winner_and_completed_lesson_is_read_only(self):
        m2=self.login('M');other=copy.deepcopy(self.doc);other['plan'][0]['title']='Other tab'
        with ThreadPoolExecutor(2)as pool:results=list(pool.map(lambda pair:self.write(*pair),[(self.doc,self.m),(other,m2)]))
        self.assertEqual(sorted(r.status_code for r in results),[200,409])
        expected=self.read().json()
        self.assertEqual(self.m.post(self.path+'/start').status_code,200)
        self.assertEqual(self.m.post(self.path+'/complete').status_code,200)
        d=copy.deepcopy(expected);d['step']=1
        self.assertEqual(self.write(d).status_code,409)
        self.assertEqual(self.read(self.a).json(),expected)
    def test_failed_durable_write_is_not_returned_to_participants(self):
        fail=[False]
        def commit():
            if fail[0]:raise RuntimeError('synthetic durable failure')
        self.build(commit);self.m=self.login('M');self.a=self.login('A');fail[0]=True
        self.assertEqual(self.write().status_code,503)
        self.assertEqual(self.read(self.a).status_code,503)
        self.assertFalse(self.a.get('/api/harness/health').json()['durability_ready'])
