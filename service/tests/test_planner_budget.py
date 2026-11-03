"""Planner factory through the real adapter and budget; in-memory HTTP only."""
import json,tempfile,unittest
from pathlib import Path
import httpx
from service.app import _build_real_adapter,PersistenceError
from harness.budget import BudgetGuard,BudgetExceeded

class PlannerBudget(unittest.TestCase):
    def build(self,total='0.25',persist=None):
        temp=tempfile.TemporaryDirectory(prefix='cx1-planner-budget-',dir='/private/tmp'if Path('/private/tmp').is_dir()else None);self.addCleanup(temp.cleanup);root=Path(temp.name)
        cfg=root/'budget.yaml';ledger=root/'budget_ledger.sqlite3';cfg.write_text(f'total_usd: {total}\nhard_stop_pct: 0.95\nledger: {ledger}\n')
        guard=BudgetGuard.initialize_ledger(str(cfg));self.requests=[]
        def handler(request):
            self.assertEqual(guard.status()['holds'],1);self.requests.append(json.loads(request.content))
            return httpx.Response(200,json={'object':'response','model':'muse-wonder-1.0','status':'completed',
                'output':[{'type':'message','role':'assistant','content':[{'type':'output_text','text':'{"plan":[{"title":"Pulse","duration":"","goal":"Keep time.","tips":[]}]}'}]}],
                'usage':{'input_tokens':20,'output_tokens':40,'total_tokens':60,'input_tokens_details':{'cached_tokens':0},'output_tokens_details':{'reasoning_tokens':10}}})
        adapter,ready=_build_real_adapter(str(root),{'MODEL_API_KEY':'offline-fixture'},on_write=persist,transport=httpx.MockTransport(handler));self.assertTrue(ready);self.addCleanup(adapter.http.close);return adapter,guard
    def test_factory_connects_wonder_responses_with_structured_plan_and_shared_guard(self):
        persisted=[];adapter,guard=self.build(persist=lambda:persisted.append(True));result=adapter.complete('orchestrator','teacher-led','goal')
        self.assertIn('Pulse',result['text']);body=self.requests[0];self.assertEqual(body['model'],'muse-wonder-1.0');self.assertEqual(body['max_output_tokens'],4096)
        self.assertEqual(body['text']['format']['name'],'lesson_plan_proposal');self.assertTrue(body['text']['format']['strict']);self.assertIs(body['store'],False)
        self.assertEqual((guard.status()['calls'],guard.status()['holds']),(1,0));self.assertEqual(len(persisted),2)
        self.assertEqual(adapter.cfg['roles']['interpreter']['endpoint'],'/chat/completions');self.assertEqual(adapter.cfg['roles']['interpreter']['max_tokens'],1024)
    def test_insufficient_budget_never_posts_or_reserves(self):
        adapter,guard=self.build('0.001')
        with self.assertRaises(BudgetExceeded):adapter.complete('orchestrator','system','goal')
        self.assertEqual(self.requests,[]);self.assertEqual((guard.status()['calls'],guard.status()['holds']),(0,0))
    def test_failed_reservation_persistence_retains_hold_and_never_posts(self):
        def fail():raise PersistenceError('fixture commit failure')
        adapter,guard=self.build(persist=fail)
        with self.assertRaises(PersistenceError):adapter.complete('orchestrator','system','goal')
        self.assertEqual(self.requests,[]);self.assertEqual(guard.status()['holds'],1)
