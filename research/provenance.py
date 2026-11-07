"""Content integrity and reproducibility, not proof of authorship or clinical truth."""
import hashlib
import hmac
import json
from pathlib import Path


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def implementation_hashes():
    root = Path(__file__).resolve().parents[1]
    paths = ['run_prototype.py', 'agents/barrier_detector.py', 'agents/task_detector.py',
             'agents/recommendation_agent.py', 'policy/policy_engine.py', 'policy/approval_gate.py',
             'research/agent.py', 'research/safety.py', 'research/quality.py', 'research/provenance.py',
             'research/representation.py', 'research/rl.py', 'research/experiments.py', 'research/service.py',
             'agents/input_reader.py', 'agents/case_analyzer.py', 'agents/readiness_explainer.py',
             'agents/output_composer.py', 'llm/llm_client.py', 'api/main.py', 'db/repository.py', 'db/models.py', 'db/migrate.py', 'db/review_repository.py',
             'api/storage_routes.py', 'api/readiness.py', 'synthesis/generate.py']
    return {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in paths if (root / p).is_file()}


def seal(record, artifacts, configuration, signing_key=None):
    payload = {'schema_version': 'research-integrity-v1', 'input_sha256': digest(record),
               'artifact_sha256': digest(artifacts), 'configuration': configuration,
               'implementation_sha256': implementation_hashes()}
    manifest = {**payload, 'manifest_sha256': digest(payload),
            'scope': 'Unkeyed content hashes detect changes relative to this manifest; they do not authenticate a person, institution, or clinical fact.'}
    if signing_key:
        manifest['signature'] = hmac.new(signing_key.encode(), manifest['manifest_sha256'].encode(), hashlib.sha256).hexdigest()
        manifest['signature_algorithm'] = 'hmac-sha256'
    return manifest


def verify(manifest, record, artifacts):
    payload = {k: v for k, v in manifest.items() if k not in ('manifest_sha256', 'scope', 'signature', 'signature_algorithm')}
    return (manifest.get('manifest_sha256') == digest(payload)
            and manifest.get('input_sha256') == digest(record)
            and manifest.get('artifact_sha256') == digest(artifacts))


def authenticate(manifest, signing_key):
    """Key-holder authenticity only. Requires a separately trusted secret key."""
    if not signing_key or manifest.get('signature_algorithm') != 'hmac-sha256': return False
    if not isinstance(manifest.get('manifest_sha256'), str) or not isinstance(manifest.get('signature'), str): return False
    payload = {k:v for k,v in manifest.items() if k not in ('manifest_sha256','scope','signature','signature_algorithm')}
    if manifest['manifest_sha256'] != digest(payload): return False
    expected = hmac.new(signing_key.encode(), manifest['manifest_sha256'].encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, manifest['signature'])
