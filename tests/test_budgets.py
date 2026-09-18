import tempfile
import unittest
from pathlib import Path

from stillpoint.budgets import BudgetExceeded, BudgetLimits, observe_tool_invocations
from stillpoint.db import CompanyDB
from stillpoint.providers.base import ProviderResult
from stillpoint.registry import AgentRegistry
from stillpoint.runtime import CompanyRuntime

ROOT=Path(__file__).resolve().parents[1]

class CountProvider:
    default_model='count'
    def __init__(self):self.calls=0
    def generate(self,**kwargs):
        self.calls+=1
        if kwargs.get('json_schema_name')=='authority_assessment':
            return ProviderResult(text='{"action_family":"none","mode":"unknown","target":"unknown","confidence":0.5,"reason":"none"}',model='count',usage={'total_tokens':2})
        return ProviderResult(text='ok',model='count',usage={'total_tokens':3})

class BudgetTests(unittest.TestCase):
    def make(self,tmp,p,budget):
        return CompanyRuntime(root=tmp,db=CompanyDB(tmp/'db.sqlite'),registry=AgentRegistry(ROOT/'config'/'agents.json'),provider=p,default_model='count',smart_routing=False,default_budget=budget)

    def test_model_call_budget_stops_future_call(self):
        with tempfile.TemporaryDirectory() as d:
            p=CountProvider();rt=self.make(Path(d),p,BudgetLimits(max_model_calls=1))
            with self.assertRaises(BudgetExceeded):rt.submit('Rewrite chapter 3 in my voice.')
            task=rt.db.list_tasks(1)[0]
            self.assertEqual(task['status'],'blocked')
            self.assertEqual(p.calls,1)
            self.assertEqual(rt.db.get_task_usage(task['id'])['model_calls'],1)
            rt.db.close()

    def test_token_usage_accumulates(self):
        with tempfile.TemporaryDirectory() as d:
            p=CountProvider();rt=self.make(Path(d),p,BudgetLimits(max_model_calls=5,max_total_tokens=20))
            out=rt.submit('Rewrite chapter 3 in my voice.')
            usage=rt.db.get_task_usage(out.task_id)
            self.assertGreaterEqual(usage['model_calls'],2)
            self.assertGreaterEqual(usage['total_tokens'],5)
            rt.db.close()

    def test_tool_offers_are_not_tool_invocations(self):
        result=ProviderResult(
            text='ok',
            model='count',
            raw={'output':[
                {'type':'web_search_call','id':'a'},
                {'type':'message','content':[{'type':'output_text','text':'ok'}]},
                {'type':'code_interpreter_call','id':'b'},
            ]},
            usage={'total_tokens':4},
        )
        count,known=observe_tool_invocations(result,tool_offers=5)
        self.assertTrue(known)
        self.assertEqual(count,2)

    def test_missing_invocation_surface_is_unknown_not_zero(self):
        result=ProviderResult(text='ok',model='count',raw={},usage={'total_tokens':4})
        count,known=observe_tool_invocations(result,tool_offers=2)
        self.assertEqual(count,0)
        self.assertFalse(known)

    def test_usage_records_offers_invocations_and_exact_xai_cost_separately(self):
        with tempfile.TemporaryDirectory() as d:
            rt=self.make(Path(d),CountProvider(),BudgetLimits(max_model_calls=5))
            task=rt.db.create_task('budget evidence')
            rt.db.set_task_budget(task,BudgetLimits(max_model_calls=5))
            result=ProviderResult(
                text='ok',
                model='count',
                raw={'output':[{'type':'web_search_call','id':'a'}]},
                usage={'total_tokens':7,'cost_in_usd_ticks':10_000_000},
            )
            rt._budget_after_call(
                task,
                result=result,
                usage=result.usage,
                tool_offers=3,
                tool_invocations=1,
                tool_invocations_known=True,
            )
            usage=rt.db.get_task_usage(task)
            self.assertEqual(usage['tool_calls'],3)  # legacy alias: offers
            self.assertEqual(usage['tool_offers'],3)
            self.assertEqual(usage['tool_invocations'],1)
            self.assertEqual(usage['tool_invocation_unknown_calls'],0)
            self.assertAlmostEqual(usage['cost_usd'],0.001)
            self.assertEqual(usage['cost_unknown_calls'],0)
            rt.db.close()

    def test_tool_budget_does_not_charge_offers_but_detects_observed_overage(self):
        with tempfile.TemporaryDirectory() as d:
            rt=self.make(Path(d),CountProvider(),BudgetLimits(max_tool_calls=1))
            task=rt.db.create_task('tool budget')
            rt.db.set_task_budget(task,BudgetLimits(max_tool_calls=1))
            # Five tools offered is not five calls; the provider has not run yet.
            rt._budget_before_call(task,tool_offers=5)
            result=ProviderResult(
                text='ok',
                model='count',
                raw={'output':[
                    {'type':'web_search_call','id':'a'},
                    {'type':'web_search_call','id':'b'},
                ]},
                usage={'total_tokens':5,'cost_in_usd_ticks':0},
            )
            with self.assertRaisesRegex(BudgetExceeded,'exceeded by provider response'):
                rt._budget_after_call(
                    task,
                    result=result,
                    usage=result.usage,
                    tool_offers=5,
                    tool_invocations=2,
                    tool_invocations_known=True,
                )
            usage=rt.db.get_task_usage(task)
            self.assertEqual(usage['tool_offers'],5)
            self.assertEqual(usage['tool_invocations'],2)
            rt.db.close()

    def test_unknown_tool_invocation_evidence_halts_bounded_task(self):
        with tempfile.TemporaryDirectory() as d:
            rt=self.make(Path(d),CountProvider(),BudgetLimits(max_tool_calls=2))
            task=rt.db.create_task('unknown tools')
            rt.db.set_task_budget(task,BudgetLimits(max_tool_calls=2))
            result=ProviderResult(text='ok',model='count',raw={},usage={'total_tokens':5,'cost_in_usd_ticks':0})
            with self.assertRaisesRegex(BudgetExceeded,'did not expose invocation evidence'):
                rt._budget_after_call(
                    task,
                    result=result,
                    usage=result.usage,
                    tool_offers=1,
                    tool_invocations=0,
                    tool_invocations_known=False,
                )
            usage=rt.db.get_task_usage(task)
            self.assertEqual(usage['tool_invocation_unknown_calls'],1)
            with self.assertRaisesRegex(BudgetExceeded,'prior invocation count is unknown'):
                rt._budget_before_call(task,tool_offers=1)
            rt.db.close()

    def test_unknown_cost_is_recorded_unknown_and_halts_cost_bounded_task(self):
        with tempfile.TemporaryDirectory() as d:
            rt=self.make(Path(d),CountProvider(),BudgetLimits(max_cost_usd=1.0))
            task=rt.db.create_task('unknown cost')
            rt.db.set_task_budget(task,BudgetLimits(max_cost_usd=1.0))
            result=ProviderResult(text='ok',model='count',raw={'output':[]},usage={'total_tokens':5})
            with self.assertRaisesRegex(BudgetExceeded,'did not expose billed cost'):
                rt._budget_after_call(
                    task,
                    result=result,
                    usage=result.usage,
                    tool_offers=0,
                    tool_invocations=0,
                    tool_invocations_known=True,
                )
            usage=rt.db.get_task_usage(task)
            self.assertEqual(usage['cost_usd'],0.0)
            self.assertEqual(usage['cost_unknown_calls'],1)
            with self.assertRaisesRegex(BudgetExceeded,'prior provider cost is unknown'):
                rt._budget_before_call(task,tool_offers=0)
            rt.db.close()

if __name__=='__main__':unittest.main()
