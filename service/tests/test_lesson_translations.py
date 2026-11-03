"""Scoped, version-bound material translation through explicit offline models."""
import copy,json,sqlite3,threading,unittest
from concurrent.futures import ThreadPoolExecutor
from service.tests import test_participants as participants
SOURCE={'title':'Chord change','duration':'4 min','goal':'Play note F-sharp on beat 1.','tips':['Do not speed up.']}
TARGET={'title':'Đổi hợp âm','duration':'4 phút','goal':'Chơi nốt Fa thăng ở phách 1.','tips':['Đừng tăng tốc.']}
class PlanAdapter:
    asr_enabled=False
    def __init__(self,directory):self.directory=directory;self.roles=[];self.raw=json.dumps(TARGET);self.review={'verdict':'faithful','reason':'Fields preserve the instruction.'};self.entered=self.release=None
    def complete(self,role,system,user):
        self.roles.append(role)
        with sqlite3.connect(self.directory+'/service.sqlite3')as c:
            assert c.execute("SELECT COUNT(*)FROM lesson_translations WHERE state='processing'").fetchone()[0]>0
        if role=='lesson_interpreter':
            if self.entered:self.entered.set();self.release.wait(5)
            return {'text':self.raw}
        if role!='lesson_reviewer':raise AssertionError('wrong role')
        if isinstance(self.review,Exception):raise self.review
        return {'text':json.dumps(self.review)}
class LessonTranslations(unittest.TestCase):
    def setUp(self):
        participants.ParticipantIntegration.setUpClass();self.p=participants.ParticipantIntegration('test_logout_revokes_cookie');self.p.setUp();self.addCleanup(self.p.doCleanups)
        self.adapter=PlanAdapter(self.p.directory.name);self.p.adapter=self.adapter;self.p.build();self.p.m=self.p.login('M');self.p.a=self.p.login('A');self.p.create()
        self.doc={'revision':0,'plan':[copy.deepcopy(SOURCE),{'title':'Other','duration':'','goal':'','tips':[]}],'step':0,'notebook':{'chords':['F#'],'notation':'','tabs':''}}
        r=self.p.m.post(self.p.path+'/lesson',json=self.doc);self.assertEqual(r.status_code,200,r.text);self.doc=r.json();self.route=self.p.path+'/lesson/translations';self.body={'revision':self.doc['revision'],'step':0,'client_event_id':'translate-1'}
    def create(self,body=None):return self.p.m.post(self.route,json=body or self.body)
    def view(self,client=None):return (client or self.p.m).get(self.route).json()
    def approve(self,job,client=None,confirm=True):return (client or self.p.m).post(self.route+'/'+job['id']+'/approve',json={'confirm_flagged':confirm})
    def test_fields_stay_private_until_required_review_and_maestro_confirmation(self):
        r=self.create();self.assertEqual(r.status_code,201,r.text);job=r.json();self.assertEqual(job['state'],'flagged');self.assertEqual(job['target'],TARGET);self.assertEqual(job['review']['state'],'complete')
        self.assertNotIn('Đổi hợp âm',json.dumps(self.view(self.p.a),ensure_ascii=False));self.assertNotIn('review',json.dumps(self.view(self.p.a)))
        self.assertEqual(self.approve(job,confirm=False).status_code,409);self.assertEqual(self.approve(job,self.p.a).status_code,403)
        self.assertEqual(self.approve(job).status_code,200);self.assertEqual(self.view(self.p.a)['steps'][0]['target'],TARGET)
        self.assertEqual(self.p.a.get(self.p.path).json()['lesson_translations']['steps'][0]['target'],TARGET)
        self.assertEqual(self.adapter.roles,['lesson_interpreter','lesson_reviewer'])
    def test_replay_cache_and_restart_never_repeat_inference(self):
        job=self.create().json();self.assertEqual(self.create().json(),job)
        self.assertEqual(self.create({**self.body,'client_event_id':'alias'}).json(),job);self.assertEqual(len(self.adapter.roles),2)
        self.assertEqual(self.create({**self.body,'step':1}).status_code,409)
        self.p.build();m=self.p.login('M');self.assertEqual(m.get(self.route).json()['steps'][0]['id'],job['id']);self.assertEqual(len(self.adapter.roles),2)
    def test_step_selection_and_notebook_keep_approval_but_source_edit_invalidates(self):
        job=self.create().json();self.assertEqual(self.approve(job).status_code,200)
        self.doc['step']=1;self.doc['notebook']['chords']=['G'];self.doc=self.p.m.post(self.p.path+'/lesson',json=self.doc).json()
        self.assertEqual(self.view(self.p.a)['steps'][0]['target'],TARGET)
        self.doc['plan'][0]['goal']='Play note G on beat 2.';self.assertEqual(self.p.m.post(self.p.path+'/lesson',json=self.doc).status_code,200)
        self.assertNotIn('target',self.view(self.p.a)['steps'][0]);self.assertEqual(self.approve(job).status_code,409)
    def test_permissions_origin_stale_revision_and_extra_fields_fail_before_models(self):
        for name in ['other']:
            other=self.p.login(name);self.assertEqual(other.get(self.route).status_code,404);self.assertIn(other.post(self.route,json=self.body).status_code,[403,404])
        self.assertEqual(self.p.a.post(self.route,json=self.body).status_code,403)
        self.assertEqual(self.p.m.post(self.route,headers={'Origin':'https://evil.invalid'},json=self.body).status_code,403)
        self.assertEqual(self.create({**self.body,'revision':0}).status_code,409)
        self.assertEqual(self.create({**self.body,'target_lang':'en'}).status_code,422);self.assertEqual(self.adapter.roles,[])
    def test_malformed_or_misaligned_structured_reply_never_becomes_a_draft(self):
        bad=[json.dumps({**TARGET,'extra':'invented'}),json.dumps({**TARGET,'tips':[]}),'{"title":"a","title":"b"}', 'Plain translation']
        for i,raw in enumerate(bad):
            self.adapter.raw=raw;r=self.create({**self.body,'client_event_id':'bad-'+str(i),'retry':i>0});self.assertEqual(r.status_code,502,r.text)
        self.assertNotIn('target',self.view(self.p.a)['steps'][0]);self.assertNotIn('lesson_reviewer',self.adapter.roles)
    def test_failed_review_blocks_even_explicit_confirmation(self):
        self.adapter.review=RuntimeError('offline reviewer failed');r=self.create();self.assertEqual(r.status_code,201,r.text);job=r.json();self.assertEqual(job['review']['state'],'failed');self.assertEqual(self.approve(job).status_code,409)
        self.assertNotIn('target',self.view(self.p.a)['steps'][0]);self.assertEqual(len(self.adapter.roles),2)
    def test_source_change_during_inference_discards_without_second_paid_stage(self):
        self.adapter.entered=threading.Event();self.adapter.release=threading.Event()
        with ThreadPoolExecutor(1)as pool:
            future=pool.submit(self.create);self.assertTrue(self.adapter.entered.wait(3));self.doc['plan'][0]['title']='Changed source';self.assertEqual(self.p.m.post(self.p.path+'/lesson',json=self.doc).status_code,200);self.adapter.release.set();r=future.result()
        self.assertEqual(r.status_code,409,r.text);self.assertEqual(self.adapter.roles,['lesson_interpreter']);self.assertNotIn('target',self.view(self.p.a)['steps'][0])
    def test_completed_meeting_cannot_generate_or_approve_and_corrupt_target_is_hidden(self):
        job=self.create().json()
        with sqlite3.connect(self.p.directory.name+'/service.sqlite3')as c:c.execute('UPDATE lesson_translations SET target_json=? WHERE id=?',('{"title":"corrupt"}',job['id']))
        self.assertEqual(self.approve(job).status_code,409);self.assertNotIn('target',self.view(self.p.a)['steps'][0])
        self.p.m.post(self.p.path+'/start');self.p.m.post(self.p.path+'/complete')
        self.assertEqual(self.create({**self.body,'client_event_id':'closed'}).status_code,409);self.assertEqual(self.approve(job).status_code,409)
    def test_explicit_retry_after_review_failure_reuses_canonical_translation(self):
        self.adapter.review=RuntimeError('review failed');self.create();self.adapter.review={'verdict':'faithful','reason':'Reviewed canonical fields.'}
        r=self.create({**self.body,'client_event_id':'retry-review','retry':True});self.assertEqual(r.status_code,201,r.text);self.assertEqual(r.json()['review']['state'],'complete')
        self.assertEqual(self.adapter.roles,['lesson_interpreter','lesson_reviewer','lesson_reviewer'])
    def test_regeneration_keeps_old_approved_until_new_confirmation_and_blocks_old_pending_approval(self):
        old=self.create().json();self.assertEqual(self.approve(old).status_code,200)
        new_target={**TARGET,'goal':'Chơi nốt Fa thăng tại phách 1.'};self.adapter.raw=json.dumps(new_target)
        fresh=self.create({**self.body,'client_event_id':'regenerate','retry':True});self.assertEqual(fresh.status_code,201,fresh.text);self.assertNotEqual(fresh.json()['id'],old['id'])
        self.assertEqual(self.view(self.p.a)['steps'][0]['target'],TARGET)
        self.assertEqual(self.approve(fresh.json()).status_code,200);self.assertEqual(self.view(self.p.a)['steps'][0]['target'],new_target)
    def test_processing_restart_fails_closed_without_replaying_models(self):
        job=self.create().json()
        with sqlite3.connect(self.p.directory.name+'/service.sqlite3')as c:c.execute("UPDATE lesson_translations SET state='processing' WHERE id=?",(job['id'],))
        count=len(self.adapter.roles);self.p.build();self.p.m=self.p.login('M');self.p.a=self.p.login('A')
        self.assertEqual(self.view()['steps'][0]['state'],'failed');self.assertEqual(self.create().status_code,502);self.assertEqual(len(self.adapter.roles),count)
    def test_older_pending_version_cannot_override_a_new_approved_translation(self):
        old=self.create().json();new=self.create({**self.body,'client_event_id':'new-version','retry':True}).json();self.assertEqual(self.approve(new).status_code,200);self.assertEqual(self.approve(old).status_code,409)
    def test_reverse_vi_to_en_uses_meeting_languages(self):
        r=self.p.m.post('/api/harness/sessions',json={'kind':'individual','league':'string','maestro_alias':'M','artist_alias':'A','artist_id':'A','source_lang':'vi','target_lang':'en'});self.assertEqual(r.status_code,201)
        self.p.path='/api/harness/sessions/'+r.json()['id'];self.route=self.p.path+'/lesson/translations';doc=copy.deepcopy(self.doc);doc['revision']=0;doc['plan'][0]=copy.deepcopy(TARGET);doc=self.p.m.post(self.p.path+'/lesson',json=doc).json();self.body['revision']=doc['revision'];self.adapter.raw=json.dumps(SOURCE)
        job=self.create().json();self.assertEqual(self.approve(job).status_code,200);view=self.view(self.p.a);self.assertEqual((view['source_lang'],view['target_lang']),('vi','en'));self.assertEqual(view['steps'][0]['target'],SOURCE)
    def test_failed_attempt_requires_explicit_retry_even_with_a_new_event_id(self):
        self.adapter.raw='malformed';self.assertEqual(self.create().status_code,502);before=len(self.adapter.roles)
        self.assertEqual(self.create({**self.body,'client_event_id':'new-id-without-retry'}).status_code,409);self.assertEqual(len(self.adapter.roles),before)
        self.adapter.raw=json.dumps(TARGET);r=self.create({**self.body,'client_event_id':'explicit-retry','retry':True});self.assertEqual(r.status_code,201,r.text)
    def test_other_maestro_cannot_read_or_generate_this_meetings_material(self):
        accounts=json.loads(self.p.env['SOM_WEB_ACCOUNTS']);accounts['otherM']={**accounts['M']};self.p.env['SOM_WEB_ACCOUNTS']=json.dumps(accounts);self.p.build();other=self.p.login('otherM')
        self.assertEqual(other.get(self.route).status_code,404);self.assertEqual(other.post(self.route,json=self.body).status_code,404);self.assertEqual(self.adapter.roles,[])
    def test_numeric_and_negation_changes_are_flagged_per_field(self):
        self.adapter.raw=json.dumps({**TARGET,'duration':'5 phút','tips':['Hãy tăng tốc.']});job=self.create().json();self.assertEqual(job['state'],'flagged');self.assertTrue(any(i.startswith('duration:')for i in job['issues']));self.assertTrue(any(i.startswith('tips.0:')for i in job['issues']));self.assertNotIn('target',self.view(self.p.a)['steps'][0])
    def test_meeting_completion_during_interpreter_discards_before_reviewer(self):
        self.assertEqual(self.p.m.post(self.p.path+'/start').status_code,200);self.adapter.entered=threading.Event();self.adapter.release=threading.Event()
        with ThreadPoolExecutor(1)as pool:
            future=pool.submit(self.create);self.assertTrue(self.adapter.entered.wait(3));self.assertEqual(self.p.m.post(self.p.path+'/complete').status_code,200);self.adapter.release.set();r=future.result()
        self.assertEqual(r.status_code,409,r.text);self.assertEqual(self.adapter.roles,['lesson_interpreter']);self.assertNotIn('target',self.view(self.p.a)['steps'][0])
