"""Bounded inspect/verify/route agent with read-only tools and explicit transitions."""
from research.provenance import digest
from research.quality import assess
from research.safety import injection_signals, verify_recommendations, governance


class WorkflowAgent:
    def __init__(self, max_steps=8):
        if not isinstance(max_steps, int) or max_steps < 1 or max_steps > 32:
            raise ValueError('max_steps must be between 1 and 32')
        self.max_steps = max_steps

    def run(self, record, barriers, tasks, proposals):
        trace, outputs = [], {}
        def tool(name, arguments, function):
            if len(trace) >= self.max_steps:
                raise RuntimeError('step_budget_exhausted')
            value = function()
            previous = trace[-1]['event_sha256'] if trace else None
            event = {'step': len(trace) + 1, 'tool': name, 'arguments_sha256': digest(arguments),
                     'result_sha256': digest(value), 'previous_sha256': previous}
            event['event_sha256'] = digest(event)
            trace.append(event)
            return value
        status = 'completed'
        try:
            outputs['source_quality'] = tool('inspect_source', record, lambda: assess(record))
            outputs['injection_signals'] = tool('scan_instruction_like_text', record, lambda: injection_signals(record))
            outputs['verification'] = tool('verify_proposals', proposals, lambda: verify_recommendations(record, barriers, tasks, proposals))
            verified = outputs['verification']['accepted']
            outputs['routes'] = tool('route_verified_proposals', verified, lambda: [
                {'task_id': p['task_id'], **governance(p)} for p in verified])
            needs_review = (outputs['source_quality']['requires_review'] or outputs['verification']['requires_review']
                            or bool(outputs['injection_signals']))
            outputs['decision'] = 'request_human_review' if needs_review else 'publish_verified_proposals'
            if needs_review:
                # Quality/injection concerns cannot be bypassed by a valid task identifier.
                for route in outputs['routes']:
                    if route['approval']['approval_status'] != 'blocked':
                        route['approval'].update(approval_status='requires_human_approval',
                            requires_human_approval=True, reason='Source quality or proposal verification requires review.')
                outputs['clarification_request'] = tool('request_review', outputs['source_quality'], lambda: {
                    'status': 'proposed_only', 'recipient_role': 'Research Reviewer',
                    'issue_ids': [i['issue_id'] for i in outputs['source_quality']['issues']],
                    'rejected_count': len(outputs['verification']['rejected']),
                    'missing_task_ids': outputs['verification']['missing_task_ids'],
                    'instruction_signal_count': len(outputs['injection_signals']), 'message_sent': False})
        except RuntimeError:
            status = 'budget_exhausted'
            outputs['decision'] = 'request_human_review'
        return {'agent': 'WorkflowAgent', 'controller': 'deterministic_finite_state', 'status': status,
                'max_steps': self.max_steps, 'steps_used': len(trace), 'trace': trace, **outputs,
                'execution_performed': False,
                'scope': 'Tool observations and decision transitions, not hidden model reasoning. No external write tools.'}
