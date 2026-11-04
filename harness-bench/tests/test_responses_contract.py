"""Real HTTP adapter contract; no provider traffic and separate fixture ledgers."""
import copy,json,tempfile,unittest
from pathlib import Path
import httpx
from harness.adapters.meta import MetaAdapter,ConfigError,MetaResponseError,MetaTransportError,MetaAPIError
from harness.budget import BudgetGuard,BudgetExceeded

FORMAT={'type':'json_schema','json_schema':{'name':'plan','strict':True,'schema':{'type':'object','properties':{'plan':{'type':'array','items':{'type':'string'}}},'required':['plan'],'additionalProperties':False}}}
def reply():
    return {'object':'response','model':'muse-wonder-1.0','status':'completed','output':[{'type':'reasoning','summary':[]},{'type':'message','role':'assistant','status':'completed','content':[{'type':'output_text','text':'{"plan": ["Play slowly"]}'}]}],
            'usage':{'input_tokens':100,'output_tokens':50,'total_tokens':150,'input_tokens_details':{'cached_tokens':20},'output_tokens_details':{'reasoning_tokens':30}}}

class ResponsesContract(unittest.TestCase):
    def build(self,data=None,total=1,handler=None,role=None):
        temp=tempfile.TemporaryDirectory(prefix='cx1-responses-',dir='/private/tmp'if Path('/private/tmp').is_dir()else None);self.addCleanup(temp.cleanup);root=Path(temp.name)
        cfg=root/'budget.yaml';cfg.write_text(f'total_usd: {total}\nhard_stop_pct: 0.95\nledger: {root}/ledger.sqlite3\n')
        guard=BudgetGuard.initialize_ledger(str(cfg));calls=[]
        def respond(request):
            self.assertEqual(guard.status()['holds'],1);calls.append(request)
            return handler(request)if handler else httpx.Response(200,json=data or reply())
        rc={'model':'muse-wonder-1.0','endpoint':'/responses','max_tokens':2048,'reasoning_effort':'low','temperature':0.1,'response_format':copy.deepcopy(FORMAT)}
        if role:rc.update(role)
        adapter=MetaAdapter({'roles':{'orchestrator':rc}},guard,transport=httpx.MockTransport(respond),environ={'MODEL_API_KEY':'offline-fixture'})
        self.addCleanup(adapter.http.close);return adapter,guard,calls
    def test_stateless_strict_request_reserves_before_http_and_accounts_reasoning_once(self):
        a,g,c=self.build();result=a.complete('orchestrator','Teacher leads.','Goals')
        self.assertEqual(result['text'],'{"plan": ["Play slowly"]}');self.assertEqual(result['cost_usd'],0.0014)
        body=json.loads(c[0].content);self.assertEqual(str(c[0].url),'https://api.meta.ai/v1/responses')
        self.assertEqual(body['input'],'Goals');self.assertEqual(body['instructions'],'Teacher leads.')
        self.assertEqual(body['max_output_tokens'],2048);self.assertEqual(body['reasoning'],{'effort':'low'})
        self.assertEqual(body['text']['format'],{'type':'json_schema',**FORMAT['json_schema']})
        self.assertIs(body['store'],False);self.assertIs(body['stream'],False);self.assertIs(body['background'],False)
        self.assertNotIn('tools',body);self.assertNotIn('previous_response_id',body);self.assertNotIn('messages',body)
        self.assertEqual(g.status()['holds'],0);self.assertEqual(g.status()['calls'],1)
    def test_preflight_denies_bad_config_large_request_and_insufficient_funds_without_http(self):
        for change in [{'max_tokens':15},{'reasoning_effort':'none'},{'model':'unknown'},{'response_format':{'type':'json_object'}}]:
            with self.subTest(change=change):
                a,g,c=self.build(role=change)
                with self.assertRaises(ConfigError):a.complete('orchestrator','sys','hello')
                self.assertEqual((g.status()['calls'],len(c)),(0,0))
        a,g,c=self.build()
        with self.assertRaises(ConfigError):a.complete('orchestrator','sys','я'*32768)
        self.assertEqual((g.status()['calls'],len(c)),(0,0))
        a,g,c=self.build(total=.001)
        with self.assertRaises(BudgetExceeded):a.complete('orchestrator','sys','hello')
        self.assertEqual((g.status()['calls'],len(c)),(0,0))
    def test_invalid_accounting_retains_full_hold(self):
        variants=[None,{'input_tokens':1,'output_tokens':2},dict(reply()['usage'],extra=1),dict(reply()['usage'],total_tokens=1),dict(reply()['usage'],input_tokens_details={'cached_tokens':True}),dict(reply()['usage'],output_tokens_details={'reasoning_tokens':51})]
        for usage in variants:
            with self.subTest(usage=usage):
                data=reply();data['usage']=usage;a,g,c=self.build(data)
                with self.assertRaises(MetaResponseError):a.complete('orchestrator','sys','hello')
                self.assertEqual((g.status()['holds'],len(c)),(1,1))
    def test_unusable_output_settles_known_usage_without_delivering_fragments_or_tools(self):
        for change in [{'status':'incomplete'},{'status':'failed'},{'output':[]},{'output':[{'type':'function_call','name':'anything'}]},
                       {'output':[{'type':'message','role':'assistant','content':[{'type':'refusal','refusal':'No'}]}]},
                       {'output':[{'type':'message','role':'assistant','status':'incomplete','content':[{'type':'output_text','text':'partial'}]}]}]:
            with self.subTest(change=change):
                data=reply();data.update(change);a,g,c=self.build(data)
                with self.assertRaises(MetaResponseError):a.complete('orchestrator','sys','hello')
                self.assertEqual((g.status()['holds'],g.status()['calls']),(0,1))
    def test_http_failures_never_retry_or_release_hold(self):
        for handler,error in [(lambda r:httpx.Response(500),MetaAPIError),(lambda r:httpx.Response(200,text='bad'),MetaResponseError)]:
            a,g,c=self.build(handler=handler)
            with self.assertRaises(error):a.complete('orchestrator','sys','hello')
            self.assertEqual((g.status()['holds'],len(c)),(1,1))
        def timeout(r):raise httpx.ReadTimeout('fixture',request=r)
        a,g,c=self.build(handler=timeout)
        with self.assertRaises(MetaTransportError):a.complete('orchestrator','sys','hello')
        self.assertEqual((g.status()['holds'],len(c)),(1,1))
