import threading,unittest
from datetime import datetime,timezone
from stillpoint.signal_employee import SignalEmailEmployee,SignalEmployeeTick
T=datetime(2026,9,17,21,0,tzinfo=timezone.utc)
class Guard:
 def __init__(self):self.n=0
 def assert_current(self,**kw):self.n+=1
class Poller:
 def __init__(self,err=None):self.err=err
 def poll(self,**kw):
  if self.err:raise self.err
  return {'status':'succeeded','tasks_created':1}
class Worker:
 def __init__(self):self.executor=None
 def run_once(self,ex,**kw):self.executor=ex;g=Guard();return {'outcome':'succeeded','result':ex('t1',g),'guard':g}
class Prep:
 def __init__(self,d='draft_reply'):self.d=d
 def execute(self,t,**kw):return {'disposition':self.d,'action_id':'a1'} if self.d=='draft_reply' else {'disposition':self.d}
class Auth:
 def __init__(self,ok=True):self.ok=ok;self.calls=[]
 def authorize_prepared_reply(self,**kw):self.calls.append(kw);return {'authorized':self.ok,'warrant':'w'}
class Runtime:
 def __init__(self):self.calls=[]
 def execute_action(self,*a,**kw):self.calls.append((a,kw));return {'status':'completed'}
class Tests(unittest.TestCase):
 def build(self,*,disp='draft_reply',ok=True,pollerr=None):
  self.w=Worker();self.a=Auth(ok);self.r=Runtime();return SignalEmailEmployee(poller=Poller(pollerr),worker_service=self.w,preparer=Prep(disp),authorizer=self.a,runtime=self.r,adapter_registry='adapters',delegation_id='signal-del',continuation_facts_provider=lambda **kw:{'policy_current':True},now_fn=lambda:T)
 def test_routine_path_authorizes_and_dispatches(self):
  e=self.build();tick=e.tick();res=tick.work['result'];self.assertTrue(res['dispatched']);self.assertEqual(len(self.a.calls),1);self.assertEqual(len(self.r.calls),1);self.assertGreaterEqual(tick.work['guard'].n,2)
 def test_human_review_never_calls_authority_or_dispatch(self):
  e=self.build(disp='human_review');r=e.tick().work['result'];self.assertFalse(r['dispatched']);self.assertEqual(self.a.calls,[]);self.assertEqual(self.r.calls,[])
 def test_failed_standing_never_dispatches(self):
  e=self.build(ok=False);r=e.tick().work['result'];self.assertFalse(r['authorized']);self.assertEqual(len(self.a.calls),1);self.assertEqual(self.r.calls,[])
 def test_intake_failure_still_drains_durable_work(self):
  e=self.build(pollerr=RuntimeError('gmail down'));tick=e.tick();self.assertEqual(tick.intake['status'],'degraded');self.assertIsNotNone(tick.work);self.assertEqual(len(self.r.calls),1)
 def test_serve_records_degraded_recovered_and_stopped_transitions(self):
  e=self.build();events=[];e.health_recorder=lambda **kw:events.append(kw);stop=threading.Event();calls={'n':0}
  def tick():
   calls['n']+=1
   if calls['n']==1:raise RuntimeError('provider exploded')
   stop.set();return SignalEmployeeTick(intake={'status':'succeeded'},work=None)
  e.tick=tick;e.serve(interval_seconds=0,stop_event=stop)
  self.assertEqual([x['status'] for x in events],['degraded','recovered','stopped'])
  self.assertIn('provider exploded',events[0]['error'])
 def test_serve_without_health_evidence_fails_loudly(self):
  e=self.build();e.tick=lambda:(_ for _ in ()).throw(RuntimeError('boom'))
  with self.assertRaisesRegex(RuntimeError,'health recorder is required'):
   e.serve(interval_seconds=0,stop_event=threading.Event())
 def test_health_recorder_failure_is_not_swallowed(self):
  e=self.build();e.tick=lambda:(_ for _ in ()).throw(RuntimeError('boom'))
  def broken(**kw):raise RuntimeError('health db unavailable')
  e.health_recorder=broken
  with self.assertRaisesRegex(RuntimeError,'health db unavailable'):
   e.serve(interval_seconds=0,stop_event=threading.Event())
 def test_delegation_id_is_mandatory(self):
  with self.assertRaises(ValueError):SignalEmailEmployee(poller=Poller(),worker_service=Worker(),preparer=Prep(),authorizer=Auth(),runtime=Runtime(),adapter_registry=None,delegation_id='',continuation_facts_provider=lambda **kw:{})
if __name__=='__main__':unittest.main()
