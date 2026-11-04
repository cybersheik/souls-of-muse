"""Teacher-led planning: private proposal, durable replay and atomic adoption."""
import copy,json,sqlite3,tempfile,threading,unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI
from fastapi.testclient import TestClient
from service.app import create_app,verify_audit_chain
from service.identity import password_hash

PLAN=[{'title':'Slow chord changes','duration':'4 min','goal':'Keep a steady pulse.','tips':['Start at 60 BPM.']}]
class Planner:
    asr_enabled=False
    def __init__(self,path):self.path=path;self.calls=[];self.raw=json.dumps({'plan':PLAN});self.entered=self.release=None
    def complete(self,role,system,user):
        self.calls.append((role,json.loads(user)))
        with sqlite3.connect(self.path+'/service.sqlite3')as c:
            assert c.execute("SELECT COUNT(*) FROM lesson_plan_proposals WHERE state='processing'").fetchone()[0]>0
        if self.entered:self.entered.set();assert self.release.wait(6)
        if isinstance(self.raw,Exception):raise self.raw
        return {'text':self.raw}

class LessonPlanner(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.accounts={n:{'role':r,'password_hash':password_hash('fixture-password')}for n,r in [('M','maestro'),('A','artist'),('other','maestro')]}
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='cx1-planner-',dir='/private/tmp'if Path('/private/tmp').is_dir()else None);self.addCleanup(self.temp.cleanup)
        self.adapter=Planner(self.temp.name);self.build();self.m=self.login('M');self.a=self.login('A')
        r=self.m.post('/api/harness/sessions',json={'kind':'individual','league':'string','maestro_alias':'Maestro','artist_alias':'Artist','artist_id':'A','source_lang':'en','target_lang':'vi'})
        self.assertEqual(r.status_code,201,r.text);self.path='/api/harness/sessions/'+r.json()['id'];self.route=self.path+'/lesson/proposals'
        self.body={'revision':0,'brief':'Practice chord changes at a steady pulse.','client_event_id':'plan-one'}
    def build(self):
        self.site=FastAPI();self.site.mount('/api/harness',create_app(data_dir=self.temp.name,adapter=self.adapter,environ={'SOM_WEB_ACCOUNTS':json.dumps(self.accounts),'SOM_COOKIE_SECURE':'0'}))
    def login(self,name):
        c=TestClient(self.site,headers={'Origin':'http://testserver'});r=c.post('/api/harness/auth/login',json={'username':name,'password':'fixture-password'});self.assertEqual(r.status_code,200,r.text);return c
    def generate(self,**changes):return self.m.post(self.route,json={**self.body,**changes})
    def apply(self,job,client=None,confirm=True):return(client or self.m).post(self.route+'/'+job['id']+'/apply',json={'confirm':confirm})
    def test_only_maestro_can_draft_and_explicitly_adopt_without_exposing_brief_to_artist(self):
        r=self.generate();self.assertEqual(r.status_code,201,r.text);job=r.json();self.assertEqual(job['state'],'draft');self.assertEqual(job['plan'],PLAN)
        self.assertEqual(self.a.get(self.route).status_code,403);self.assertNotIn('lesson_planner',self.a.get(self.path).json());self.assertEqual(self.a.get(self.path+'/lesson').json()['plan'],[])
        self.assertEqual(self.apply(job,confirm=False).status_code,409);self.assertEqual(self.apply(job,self.a).status_code,403)
        self.assertEqual(self.apply(job).status_code,200);doc=self.a.get(self.path+'/lesson').json();self.assertEqual(doc['plan'],PLAN);self.assertEqual((doc['revision'],doc['step']),(1,0))
        self.assertEqual(self.apply(job).status_code,200);self.assertEqual(self.a.get(self.path+'/lesson').json()['revision'],1)
        self.assertEqual([r[0]for r in self.adapter.calls],['orchestrator']);payload=self.adapter.calls[0][1];self.assertEqual(payload['language'],'en');self.assertNotIn('Artist',json.dumps(payload))
        with sqlite3.connect(self.temp.name+'/service.sqlite3')as c:self.assertTrue(verify_audit_chain(c)[0])
    def test_replay_and_alias_cache_survive_restart_and_reject_conflicting_event(self):
        job=self.generate().json();self.assertEqual(self.generate().json(),job);self.assertEqual(self.generate(client_event_id='alias').json(),job)
        self.assertEqual(self.generate(brief='different').status_code,409);self.assertEqual(len(self.adapter.calls),1)
        self.build();self.m=self.login('M');self.assertEqual(self.m.get(self.route).json()['proposal'],job);self.assertEqual(self.generate().json(),job);self.assertEqual(len(self.adapter.calls),1)
    def test_requesting_an_earlier_cached_brief_selects_that_proposal_without_another_call(self):
        first=self.generate().json();second=self.generate(client_event_id='brief-two',brief='A different exercise.').json();self.assertNotEqual(first['id'],second['id'])
        selected=self.generate(client_event_id='back-to-one').json();self.assertEqual(selected,first)
        self.assertEqual(self.m.get(self.route).json()['proposal']['id'],first['id']);self.assertEqual(self.m.get(self.path).json()['lesson_planner']['proposal']['id'],first['id']);self.assertEqual(len(self.adapter.calls),2)
    def test_roles_membership_origin_and_revision_block_before_models(self):
        self.assertEqual(self.a.post(self.route,json=self.body).status_code,403)
        self.assertEqual(self.login('other').post(self.route,json=self.body).status_code,404)
        self.assertEqual(self.m.post(self.route,json=self.body,headers={'Origin':'https://bad.invalid'}).status_code,403)
        self.assertEqual(self.generate(revision=4).status_code,409);self.assertEqual(self.generate(model='other').status_code,422);self.assertEqual(self.generate(brief=' ').status_code,422);self.assertEqual(self.adapter.calls,[])
    def test_notebook_edit_invalidates_old_proposal_and_adoption_preserves_current_notebook(self):
        job=self.generate().json();doc=self.m.get(self.path+'/lesson').json();doc['notebook']['chords']=['F#'];doc=self.m.post(self.path+'/lesson',json=doc).json()
        self.assertIsNone(self.m.get(self.route).json()['proposal']);self.assertEqual(self.apply(job).status_code,409)
        fresh=self.generate(revision=doc['revision'],client_event_id='new-revision').json();self.assertEqual(self.apply(fresh).status_code,200);self.assertEqual(self.a.get(self.path+'/lesson').json()['notebook']['chords'],['F#'])
    def test_failed_or_interrupted_attempt_requires_explicit_retry_and_never_applies_bad_shape(self):
        self.adapter.raw=json.dumps({'plan':[{**PLAN[0],'extra':'ignored?'}]});self.assertEqual(self.generate().status_code,502)
        self.assertEqual(self.generate(client_event_id='new-id').status_code,409);self.assertEqual(len(self.adapter.calls),1)
        self.adapter.raw=json.dumps({'plan':PLAN});r=self.generate(client_event_id='retry',retry=True);self.assertEqual(r.status_code,201,r.text)
        with sqlite3.connect(self.temp.name+'/service.sqlite3')as c:c.execute("UPDATE lesson_plan_proposals SET state='processing'")
        self.build();self.m=self.login('M');self.assertEqual(self.m.get(self.route).json()['proposal']['state'],'failed');self.assertEqual(self.generate(client_event_id='after-restart').status_code,409);self.assertEqual(len(self.adapter.calls),2)
    def test_concurrent_duplicate_one_call_and_stale_result_discarded(self):
        self.adapter.entered=threading.Event();self.adapter.release=threading.Event()
        with ThreadPoolExecutor(max_workers=1)as pool:
            pending=pool.submit(self.generate);self.assertTrue(self.adapter.entered.wait(4))
            duplicate=self.generate(client_event_id='alias');self.assertEqual(duplicate.status_code,201,duplicate.text);self.assertEqual(duplicate.json()['state'],'processing')
            doc=self.m.get(self.path+'/lesson').json();doc['notebook']['tabs']='new';self.assertEqual(self.m.post(self.path+'/lesson',json=doc).status_code,200)
            self.adapter.release.set();r=pending.result(5);self.assertEqual(r.status_code,409,r.text)
        self.assertEqual(len(self.adapter.calls),1);self.assertEqual(self.a.get(self.path+'/lesson').json()['plan'],[])
    def test_completed_meeting_and_corrupt_persisted_plan_cannot_be_applied(self):
        job=self.generate().json()
        with sqlite3.connect(self.temp.name+'/service.sqlite3')as c:c.execute("UPDATE lesson_plan_proposals SET plan_json=?",(json.dumps({'plan':[]}),))
        self.assertEqual(self.apply(job).status_code,409)
        with sqlite3.connect(self.temp.name+'/service.sqlite3')as c:c.execute("UPDATE sessions SET state='completed'")
        self.assertEqual(self.generate(client_event_id='closed',retry=True).status_code,409);self.assertEqual(self.apply(job).status_code,409);self.assertEqual(len(self.adapter.calls),1)
    def test_generated_plan_must_fit_together_with_preserved_notebook_before_becoming_a_draft(self):
        doc=self.m.get(self.path+'/lesson').json();doc['notebook'].update(notation='x'*8000,tabs='y'*8000);doc=self.m.post(self.path+'/lesson',json=doc).json()
        step={'title':'p'*160,'duration':'4 min','goal':'g'*1000,'tips':['t'*400]*7};self.adapter.raw=json.dumps({'plan':[step]*3})
        r=self.generate(revision=doc['revision']);self.assertEqual(r.status_code,502,r.text);job=self.m.get(self.route).json()['proposal'];self.assertEqual(job['state'],'failed');self.assertNotIn('plan',job)
        self.assertLess(self.adapter.calls[0][1]['max_plan_array_utf8_bytes'],12000)

    def test_generated_duration_cannot_be_a_schema_placeholder(self):
        from service.lesson_planner import parse_plan
        for duration in ('4 min','one minute','until relaxed','until goal reached','string crossings for 4 min',''):
            plan=copy.deepcopy(PLAN);plan[0]['duration']=duration
            self.assertEqual(parse_plan(json.dumps({'plan':plan})),plan)
        for index,duration in enumerate(('title',' duration ','GOAL','tips','string','<duration>','"title"','`duration`','(goal)','< [ title ] >','“title”')):
            plan=copy.deepcopy(PLAN);plan[0]['duration']=duration;self.adapter.raw=json.dumps({'plan':plan})
            response=self.generate(client_event_id='placeholder-'+str(index),retry=True)
            self.assertEqual(response.status_code,502,response.text)
            self.assertEqual(self.m.get(self.route).json()['proposal']['state'],'failed')
            self.assertEqual(self.a.get(self.path+'/lesson').json()['plan'],[])

    def test_persisted_placeholder_is_unavailable_and_needs_explicit_retry(self):
        job=self.generate().json();invalid=copy.deepcopy(PLAN);invalid[0]['duration']='title'
        with sqlite3.connect(self.temp.name+'/service.sqlite3')as c:
            c.execute('UPDATE lesson_plan_proposals SET plan_json=? WHERE id=?',(json.dumps({'plan':invalid}),job['id']))
        self.assertEqual(self.m.get(self.route).json()['proposal']['state'],'unavailable')
        self.assertEqual(self.apply(job).status_code,409)
        self.assertEqual(self.generate(client_event_id='inspect-again').status_code,409)
        self.assertEqual(len(self.adapter.calls),1)
        retried=self.generate(client_event_id='explicit-retry',retry=True)
        self.assertEqual(retried.status_code,201,retried.text)
        self.assertNotEqual(retried.json()['id'],job['id']);self.assertEqual(retried.json()['plan'],PLAN)
        self.assertEqual(len(self.adapter.calls),2)
