"""Read frozen local experiment artifacts. No training inside API requests."""
import json
from pathlib import Path
import re
from research.provenance import digest
from research.representation import ContrastiveEncoder
from research.rl import WorkflowEnv, choose, ACTIONS

ROOT = Path(__file__).resolve().parents[1]
BUNDLES = ROOT/'results/research_alignment'


def load_bundle():
    pointer = BUNDLES/'active.json'
    if not pointer.is_file(): return None
    name = json.loads(pointer.read_text())['run']
    if not isinstance(name, str) or not re.fullmatch(r'run_[a-zA-Z0-9_-]+', name):
        raise ValueError('Invalid research bundle selection')
    folder = BUNDLES/name
    manifest = json.loads((folder/'manifest.json').read_text())
    values = {}
    for filename in ('report.json', 'encoder.json', 'rl_policies.json', 'retrieval_reference.json'):
        value = json.loads((folder/filename).read_text())
        if manifest['files'].get(filename) != digest(value):
            raise ValueError(f'Research artifact integrity mismatch: {filename}')
        values[filename] = value
    return name, values


def summary():
    bundle = load_bundle()
    if bundle is None: return {'status': 'not_trained', 'message': 'Run python -m research.experiments and select a frozen bundle.'}
    name, files = bundle
    report = files['report.json']
    safety = {k:v for k,v in report['safety'].items() if k != 'rows'}
    representation = report['representation']
    return {'status': 'ready', 'bundle':name, 'created_at':report['created_at'], 'safety':safety,
            'representation': {'scope':representation['scope'], 'split_counts':representation['split_counts'],
                'training':representation['training'],
                'metrics': {k:v['methods'] for k,v in representation['metrics'].items()}},
            'rl': {'scope':report['rl']['scope'], 'seeds':report['rl']['seeds'],
                   'aggregates':report['rl']['aggregates']}, 'limitations':report['limitations'],
            'artifact_integrity': 'matches_local_manifest', 'origin_authenticated':False,
            'execution_performed':False}


def neighbors(record, k=3):
    bundle = load_bundle()
    if bundle is None: return {'status':'not_trained', 'neighbors':[]}
    name, files = bundle
    encoder = ContrastiveEncoder.from_artifact(files['encoder.json'])
    return {'status':'ready', 'bundle':name, 'neighbors':encoder.nearest(record, files['retrieval_reference.json'],k),
            'scope':'Experimental similarity to synthetic training references; not evidence for a recommendation.',
            'execution_performed':False}


def simulate(kind, shield=True):
    bundle = load_bundle()
    if bundle is None: return {'status':'not_trained'}
    name, files = bundle
    policy = next(p for p in files['rl_policies.json'] if p['shield'])
    env, trace = WorkflowEnv(kind), []
    while not env.done:
        state = env.state()
        proposed = choose(policy['q_table'], state, ACTIONS)
        action = proposed if not shield or proposed in env.permitted() else env.permitted()[0]
        _, reward, _, info = env.step(action)
        trace.append({'state':state, 'proposed_action':proposed, 'applied_action':action,
                      'shield_intervened':proposed != action, 'reward':reward, **info})
    return {'status':'completed', 'bundle':name, 'scenario':kind, 'shield':shield,
            'policy_seed':policy['seed'], 'trace':trace, 'execution_performed':False,
            'scope':'Toy simulator only. This policy does not control the patient pipeline.'}
