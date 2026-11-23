import math
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from library import Library, cosine, seed
from physics import head, velocity, friction, orifice, residual, fit_models
from evaluate import metrics
from agents import hydraulic, investigator, planner, verifier

class FakeEmbedder:
    def encode(self,texts,**kwargs):
        return [[float('water' in s.lower()),float('pressure' in s.lower()),1] for s in texts]

class Tests(unittest.TestCase):
    def test_physics(self):
        self.assertAlmostEqual(head(98.1,0,0),10)
        self.assertAlmostEqual(velocity(math.pi*2.5,0.1),1)
        self.assertAlmostEqual(friction(100,0.1,1),20/19.62)
        self.assertAlmostEqual(orifice(200,0.005),0.24347343065)
    def test_models(self):
        rows=[]
        for i,p in enumerate([100,150,200,300,400]):
            q=[4,5,4,5,4][i]
            rows.append(SimpleNamespace(branch_id='A',cycle_id=str(i),q_up_l_s=q,q_down_l_s=q-0.2*p/100,p_up_kpa=p,p_down_kpa=p,pipe_storage_change_l_s=0,branch_tap_l_s=0,full_pipe_flag=True,stable_window_verified=True,meter_up_sigma_l_s=0.02,meter_down_sigma_l_s=0.02))
        self.assertAlmostEqual(residual(rows[0])[0],0.2)
        self.assertEqual(fit_models(rows)['leading'],'leak')
        self.assertEqual(fit_models(rows[:2])['status'],'insufficient distinct stable windows')
        state={'readings':rows}
        for func in (hydraulic,investigator,planner,verifier): state.update(func(state))
        self.assertIn('preliminary',state['report']['status'])
    def test_rag(self):
        self.assertAlmostEqual(cosine([1,0],[1,0]),1)
        with tempfile.TemporaryDirectory() as d:
            lib=Library(FakeEmbedder(),Path(d)/'rag.db')
            self.assertGreater(seed(lib),25)
            self.assertEqual(seed(lib),0)
            self.assertTrue(lib.search('water pressure'))
    def test_metrics(self):
        with self.assertRaises(ValueError): metrics([])
        result=metrics([{'case_id':'1','actual':'leak','prediction':'unresolved'},{'case_id':'2','actual':'normal','prediction':'normal'}])
        self.assertEqual(result['recall_pct'],0)
        self.assertEqual(result['accuracy_pct'],50)

if __name__=='__main__': unittest.main()
