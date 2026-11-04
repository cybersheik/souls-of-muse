"""Real adapter factory/budget path with an in-memory HTTP transport only."""
import json,tempfile,unittest
from pathlib import Path
import httpx
from service.app import _build_real_adapter,PersistenceError
from harness.budget import BudgetGuard,BudgetExceeded
class MaterialBudget(unittest.TestCase):
    def build(self,total='0.25',persist=None):
        directory=tempfile.TemporaryDirectory(prefix='cx1-material-budget-');self.addCleanup(directory.cleanup);root=Path(directory.name)
        cfg=root/'budget.yaml';ledger=root/'budget_ledger.sqlite3';cfg.write_text(f'total_usd: {total}\nwarn_pct: 0.8\nhard_stop_pct: 0.95\nledger: {ledger}\n')
        guard=BudgetGuard.initialize_ledger(str(cfg),str(ledger));self.requests=[]
        def response(request):
            self.assertEqual(guard.status()['holds'],1);body=json.loads(request.content);self.requests.append(body)
            content='{"title":"Đổi hợp âm","duration":"4 phút","goal":"Chơi chậm.","tips":[]}'if body['response_format']['json_schema']['name']=='lesson_step_translation'else'{"verdict":"faithful","reason":"Canonical fields preserved."}'
            return httpx.Response(200,json={'choices':[{'message':{'content':content},'finish_reason':'stop'}],'usage':{'prompt_tokens':20,'completion_tokens':20}})
        adapter,ready=_build_real_adapter(str(root),{'MODEL_API_KEY':'offline-fixture-only'},on_write=persist,transport=httpx.MockTransport(response));self.assertTrue(ready);self.addCleanup(adapter.http.close)
        return adapter,guard
    def test_both_material_roles_reserve_before_http_and_settle_same_guard(self):
        persisted=[];adapter,guard=self.build(persist=lambda:persisted.append(True))
        for role in ['lesson_interpreter','lesson_reviewer']:adapter.complete(role,'system','source')
        self.assertEqual([b['max_tokens']for b in self.requests],[8192,2048]);self.assertTrue(all(b['reasoning_effort']=='minimal'for b in self.requests));self.assertTrue(all(b['response_format']['json_schema']['strict']for b in self.requests))
        self.assertEqual(guard.status()['calls'],2);self.assertEqual(guard.status()['holds'],0);self.assertGreaterEqual(len(persisted),4)
        self.assertEqual(adapter.cfg['roles']['interpreter']['max_tokens'],1024);self.assertEqual(adapter.cfg['roles']['reviewer']['max_tokens'],512)
    def test_insufficient_allocation_stops_before_any_http_or_new_reservation(self):
        adapter,guard=self.build('0.001')
        with self.assertRaises(BudgetExceeded):adapter.complete('lesson_interpreter','system','source')
        self.assertEqual(self.requests,[]);self.assertEqual(guard.status()['calls'],0);self.assertEqual(guard.status()['holds'],0)
    def test_failed_reserve_persistence_prevents_http_and_retains_hold(self):
        def fail():raise PersistenceError('synthetic volume failure')
        adapter,guard=self.build(persist=fail)
        with self.assertRaises(PersistenceError):adapter.complete('lesson_interpreter','system','source')
        self.assertEqual(self.requests,[]);self.assertEqual(guard.status()['holds'],1)
