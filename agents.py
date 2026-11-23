"""Four deterministic agents. LLM never controls diagnoses."""
from typing import TypedDict
from physics import residual, fit_models

class State(TypedDict, total=False):
    readings: list
    balances: list
    fits: dict
    tests: list
    report: dict


def hydraulic(state):
    balances=[]
    for r in state['readings']:
        value,sigma=residual(r)
        eligible=r.full_pipe_flag and r.stable_window_verified
        balances.append({'branch':r.branch_id,'cycle':r.cycle_id,'residual_l_s':value,'sigma_l_s':sigma,'eligible':eligible,'positive_anomaly':value>3*sigma if eligible else None})
    return {'balances':balances}


def investigator(state):
    groups={}
    for r in state['readings']:
        groups.setdefault(r.branch_id,[]).append(r)
    return {'fits':{k:fit_models(v) for k,v in groups.items()}}


def planner(state):
    tests=[]
    for branch,fit in state['fits'].items():
        if fit.get('leading')=='normal' and fit['status']=='tentative':
            continue
        tests.append({'branch':branch,'recommended_tests':['Verified zero-flow offset check','Independent reference meter read at each boundary','Additional stable window at distinct pressure and flow'], 'status':'not performed; request utility staff / historical data'})
    return {'tests':tests}


def verifier(state):
    return {'report':{'status':'preliminary screening; no independent verification recorded','balances':state['balances'],'fits':state['fits'],'recommended_tests':state['tests'],'limits':'No exact position, no confirmed leak, no field accuracy. Whole-cycle fallback, adaptive test scoring, uncertainty propagation and simultaneous fault fitting remain future work.'}}


def diagnose(readings):
    from langgraph.graph import StateGraph, START, END
    from langchain_core.tools import tool
    @tool
    def calculate_hydraulics() -> str:
        """Calculate flow residuals for validated readings."""
        import json
        return json.dumps(hydraulic({'readings':readings}))
    import json
    graph=StateGraph(State)
    graph.add_node('hydraulic',lambda state:json.loads(calculate_hydraulics.invoke({})))
    graph.add_node('investigator',investigator)
    graph.add_node('planner',planner)
    graph.add_node('verifier',verifier)
    graph.add_edge(START,'hydraulic')
    graph.add_edge('hydraulic','investigator')
    graph.add_edge('investigator','planner')
    graph.add_edge('planner','verifier')
    graph.add_edge('verifier',END)
    return graph.compile().invoke({'readings':readings})['report']
