"""Account-owned notes are separate from shared lesson material and model data."""
import json,sqlite3,tempfile,unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote
from fastapi import FastAPI
from fastapi.testclient import TestClient
from service.app import create_app
from service.identity import password_hash

class NoModels:
    asr_enabled=False
    def __init__(self):self.calls=[]
    def complete(self,role,system,user):
        self.calls.append((role,user))
        if role!='orchestrator':raise AssertionError('No model call permitted')
        return {'text':'{"plan":[{"title":"Pulse","duration":"","goal":"Keep time.","tips":[]}]}'}

class PrivateNotes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.accounts={name:{'role':role,'password_hash':password_hash('fixture-password')}for name,role in [('M','maestro'),('A','artist'),('other','maestro')]}
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='cx1-private-notes-',dir='/private/tmp'if Path('/private/tmp').is_dir()else None);self.addCleanup(self.temp.cleanup);self.adapter=NoModels();self.fail_commit=False;self.build()
        self.m=self.login('M');self.a=self.login('A');self.sid=self.create();self.route='/api/harness/sessions/'+self.sid+'/notes'
    def build(self):
        def persist():
            if self.fail_commit:raise RuntimeError('fixture durability failure')
        self.site=FastAPI();self.site.mount('/api/harness',create_app(data_dir=self.temp.name,adapter=self.adapter,environ={'SOM_WEB_ACCOUNTS':json.dumps(self.accounts),'SOM_COOKIE_SECURE':'0'},maestro_token='maestro-fixture-token-private',artist_token='artist-fixture-token-private',on_write=persist))
    def login(self,name):
        c=TestClient(self.site,headers={'Origin':'http://testserver','X-SOM-Participant':quote(name,safe='')});r=c.post('/api/harness/auth/login',json={'username':name,'password':'fixture-password'});self.assertEqual(r.status_code,200,r.text);return c
    def create(self):
        r=self.m.post('/api/harness/sessions',json={'kind':'individual','league':'string','maestro_alias':'Maestro','artist_alias':'Artist','artist_id':'A','source_lang':'en','target_lang':'vi'});self.assertEqual(r.status_code,201,r.text);return r.json()['id']
    def save(self,text,revision=0,client=None):return(client or self.m).post(self.route,json={'revision':revision,'text':text})
    def test_each_participant_sees_only_own_notes_and_shared_views_do_not_leak_them(self):
        self.assertEqual(self.m.get(self.route).json(),{'revision':0,'text':''})
        self.assertEqual(self.save('Private Maestro text').status_code,200);self.assertEqual(self.save('Private Artist text',client=self.a).status_code,200)
        self.assertEqual(self.m.get(self.route).json()['text'],'Private Maestro text');self.assertEqual(self.a.get(self.route).json()['text'],'Private Artist text')
        self.assertEqual(self.a.get(self.route).headers['X-SOM-Participant'],'A')
        for client,own,other in [(self.m,'Private Maestro','Private Artist'),(self.a,'Private Artist','Private Maestro')]:
            view=client.get('/api/harness/sessions/'+self.sid).json();self.assertIn(own,json.dumps(view));self.assertNotIn(other,json.dumps(view))
            for suffix in ['/events','/audit/verify','/lesson']:
                self.assertNotIn('Private ',client.get('/api/harness/sessions/'+self.sid+suffix).text)
        self.assertEqual(self.adapter.calls,[])
    def test_exact_replay_and_conflicting_tab_do_not_increment_or_overwrite(self):
        first=self.save('one').json();self.assertEqual(first,{'revision':1,'text':'one'})
        self.assertEqual(self.save('one').json(),first);self.assertEqual(self.save('different').status_code,409)
        self.assertEqual(self.m.get(self.route).json(),first)
        self.assertEqual(self.save('',revision=1).json(),{'revision':2,'text':''})
        self.assertEqual(self.m.get('/api/harness/notes').json()['notes'],[])
    def test_ownership_is_cookie_bound_not_role_owner_field_or_legacy_token(self):
        other=self.login('other');self.assertEqual(other.get(self.route).status_code,404);self.assertEqual(other.post(self.route,json={'revision':0,'text':'foreign'}).status_code,404)
        self.assertEqual(self.m.post(self.route,json={'revision':0,'text':'x','owner':'A'}).status_code,422)
        self.assertEqual(self.m.post(self.route,json={'revision':0,'text':'x'},headers={'Origin':'https://bad.invalid'}).status_code,403)
        legacy=TestClient(self.site,headers={'Authorization':'Bearer maestro-fixture-token-private'});self.assertEqual(legacy.get(self.route).status_code,403)
        self.assertNotIn('private_notes',legacy.get('/api/harness/sessions/'+self.sid).json())
    def test_notes_survive_a_new_server_process_and_remain_editable_after_completion(self):
        self.save('Practice after the lesson.');self.build();self.m=self.login('M');self.assertEqual(self.m.get(self.route).json()['text'],'Practice after the lesson.')
        with sqlite3.connect(self.temp.name+'/service.sqlite3')as c:c.execute("UPDATE sessions SET state='completed'")
        r=self.save('Reflection after completion.',revision=1);self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['revision'],2)
    def test_plain_text_and_byte_bounds_are_validated_without_truncation_or_model_calls(self):
        self.assertEqual(self.save('<script>private</script>').json()['text'],'<script>private</script>')
        for text in ['x'*8001,'🙂'*8000]:self.assertEqual(self.save(text,revision=1).status_code,422)
        self.assertEqual(self.save('界'*8000,revision=1).status_code,200);self.assertEqual(self.adapter.calls,[])
    def test_private_note_is_not_added_to_an_explicit_planning_prompt(self):
        self.save('PRIVATE-CONTENT-NEVER-FOR-MODELS')
        r=self.m.post('/api/harness/sessions/'+self.sid+'/lesson/proposals',json={'revision':0,'brief':'Practice pulse.','client_event_id':'plan'});self.assertEqual(r.status_code,201,r.text)
        self.assertEqual(len(self.adapter.calls),1);self.assertNotIn('PRIVATE-CONTENT',self.adapter.calls[0][1])
    def test_atomic_same_owner_writes_reject_conflict_and_other_owner_is_independent(self):
        with ThreadPoolExecutor(max_workers=2)as pool:results=list(pool.map(lambda text:self.save(text),['one','two']))
        self.assertEqual(sorted(r.status_code for r in results),[200,409]);self.assertEqual(self.m.get(self.route).json()['revision'],1)
        self.assertEqual(self.save('Artist',client=self.a).status_code,200)
    def test_failed_durable_commit_blocks_note_responses_and_further_reads(self):
        self.fail_commit=True;r=self.save('not acknowledged');self.assertEqual(r.status_code,503,r.text);self.assertNotIn('not acknowledged',r.text)
        self.assertEqual(self.m.get(self.route).status_code,503);self.assertEqual(self.m.get('/api/harness/health').json()['durability_ready'],False)
    def test_corrupt_own_note_fails_closed_without_breaking_the_other_participant(self):
        self.save('valid')
        with sqlite3.connect(self.temp.name+'/service.sqlite3')as c:c.execute('UPDATE participant_notes SET text=?',('x'*8001,))
        self.assertEqual(self.m.get(self.route).status_code,503);self.assertEqual(self.m.get('/api/harness/sessions/'+self.sid).status_code,503)
        self.assertEqual(self.a.get(self.route).status_code,200)
    def test_own_index_is_paginated_and_cross_account_records_never_appear(self):
        for i in range(23):
            sid=self.sid if i==0 else self.create();r=self.m.post('/api/harness/sessions/'+sid+'/notes',json={'revision':0,'text':f'My private note {i}'});self.assertEqual(r.status_code,200,r.text)
        self.save('Artist-only index',client=self.a)
        first=self.m.get('/api/harness/notes').json();self.assertEqual(len(first['notes']),20);self.assertIsNotNone(first['next_cursor'])
        second=self.m.get('/api/harness/notes',params={'cursor':first['next_cursor']}).json();self.assertEqual(len(second['notes']),3);self.assertIsNone(second['next_cursor'])
        ids=[r['session_id']for r in first['notes']+second['notes']];self.assertEqual(len(set(ids)),23)
        artist=self.a.get('/api/harness/notes').json();self.assertEqual(len(artist['notes']),1);self.assertNotIn('My private note',json.dumps(artist))
        self.assertEqual(self.m.get('/api/harness/notes',params={'cursor':'broken'}).status_code,422)
    def test_cookie_switch_cannot_save_an_old_tab_draft_under_the_new_account(self):
        self.save('M original');self.save('A original',client=self.a)
        # HttpOnly cookies are shared between same-profile tabs. JS in the old
        # tab still expects M, while the actual browser credential now belongs A.
        switched=TestClient(self.site,cookies=self.a.cookies,headers={'Origin':'http://testserver','X-SOM-Participant':'M'})
        r=switched.post(self.route,json={'revision':1,'text':'M UNSAVED PRIVATE'});self.assertEqual(r.status_code,401,r.text)
        self.assertEqual(self.a.get(self.route).json()['text'],'A original');self.assertEqual(self.m.get(self.route).json()['text'],'M original')
        for path in [self.route,'/api/harness/sessions/'+self.sid,'/api/harness/notes','/api/harness/auth/me']:
            r=switched.get(path);self.assertEqual(r.status_code,401,r.text);self.assertNotIn('A original',r.text)
        self.assertEqual(switched.post('/api/harness/auth/logout',json={}).status_code,401)
        self.assertEqual(self.a.get('/api/harness/auth/me').status_code,200)
    def test_private_write_requires_an_account_precondition_even_with_a_valid_cookie(self):
        unbound=TestClient(self.site,cookies=self.m.cookies,headers={'Origin':'http://testserver'})
        self.assertEqual(unbound.post(self.route,json={'revision':0,'text':'unbound'}).status_code,409)
        self.assertEqual(self.m.get(self.route).json()['revision'],0)
    def test_unicode_account_context_is_encoded_in_headers_and_still_owned_by_the_cookie(self):
        name='Маэстро';self.accounts={**self.accounts,name:{'role':'maestro','password_hash':password_hash('fixture-password')}};self.build();self.m=self.login(name);self.sid=self.create();self.route='/api/harness/sessions/'+self.sid+'/notes'
        r=self.save('Моя заметка');self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.headers['X-SOM-Participant'],quote(name,safe=''));self.assertEqual(self.m.get(self.route).json()['text'],'Моя заметка')
