"""Validate proposals against current deterministic tasks; preserve rejected content."""
import copy
import re
from policy.approval_gate import ApprovalGate
from policy.policy_engine import PolicyEngine
from research.provenance import digest


def injection_signals(record):
    signals = []
    patterns = [r'ignore\s+(all\s+)?(previous|prior|system)\s+instructions',
                r'(system|developer)\s*(prompt|message)\s*:', r'bypass\s+(the\s+)?(approval|policy|safety)',
                r'<\|(?:im_start|system)\|>']
    def walk(value, path):
        if isinstance(value, dict):
            for k, v in value.items(): walk(v, f'{path}.{k}' if path else k)
        elif isinstance(value, list):
            for i, v in enumerate(value): walk(v, f'{path}[{i}]')
        elif isinstance(value, str) and any(re.search(p, value, re.I) for p in patterns):
            signals.append({'source_path': path, 'kind': 'instruction_like_text', 'value_sha256': digest(value)})
    walk(record, '')
    return signals


def verify_recommendations(record, barriers, tasks, proposals):
    from agents.barrier_detector import BarrierDetector
    from agents.task_detector import TaskDetector
    canonical_barriers = BarrierDetector().detect(record)['barriers']
    canonical_tasks = TaskDetector().detect(record, canonical_barriers)['tasks']
    trusted = barriers == canonical_barriers and tasks == canonical_tasks
    task_map = {t['task_id']: t for t in canonical_tasks}
    accepted, rejected, seen = [], [], set()
    if not isinstance(proposals, list):
        proposals = [proposals]
    for proposal in proposals:
        reasons = []
        if not trusted: reasons.append('stale_or_fabricated_detector_context')
        if not isinstance(proposal, dict):
            rejected.append({'proposal': copy.deepcopy(proposal), 'reasons': ['proposal_must_be_object']})
            continue
        if not isinstance(proposal.get('recommendation_id'), str) or not proposal['recommendation_id'].strip():
            reasons.append('invalid_recommendation_id')
        if not isinstance(proposal.get('rationale'), str): reasons.append('invalid_rationale')
        task_id = proposal.get('task_id')
        task = task_map.get(task_id) if isinstance(task_id, str) else None
        if task is None:
            reasons.append('task_not_supported_by_current_evidence')
        elif task_id in seen:
            reasons.append('duplicate_task')
        else:
            if proposal.get('action') != task['task_name']: reasons.append('action_mismatch')
            if proposal.get('owner_role') != task['owner_role']: reasons.append('owner_mismatch')
            if proposal.get('priority') != task['priority']: reasons.append('priority_mismatch')
            if proposal.get('resolves_barriers') != task['resolves_barriers']: reasons.append('barrier_mismatch')
            if proposal.get('source_fields') != [task['source_field']]: reasons.append('source_mismatch')
        operation = proposal.get('requested_operation')
        if operation is not None:
            reasons.append('execution_operation_not_permitted')
        if reasons:
            rejected.append({'proposal': copy.deepcopy(proposal), 'reasons': reasons})
        else:
            seen.add(task_id)
            item = copy.deepcopy(proposal)
            # Free-form rationale is retained as unverified model content, never approved as evidence.
            item['rationale_role'] = 'unverified_model_text'
            item['evidence_verified'] = True
            item['execution_performed'] = False
            accepted.append(item)
    missing = sorted(set(task_map) - seen)
    return {'status': 'requires_review' if rejected or missing or not trusted else 'verified',
            'accepted': accepted, 'rejected': rejected, 'missing_task_ids': missing,
            'context_verified': trusted, 'requires_review': bool(rejected or missing or not trusted),
            'execution_performed': False,
            'scope': 'Exact task/evidence consistency; free-form rationale truth is not established.'}


def governance(proposal):
    return {'policy': PolicyEngine().evaluate(proposal), 'approval': ApprovalGate().evaluate(proposal)}
