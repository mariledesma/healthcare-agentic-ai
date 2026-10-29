"""Freeze approved workflow expectations; never invent review decisions."""
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import shutil
import tempfile


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_snapshot(folder):
    index = json.loads((folder / 'checksums.json').read_text())
    expected = index['files']
    actual = {str(path.relative_to(folder)) for path in folder.rglob('*') if path.is_file() and path != folder / 'checksums.json'}
    if actual != set(expected):
        raise ValueError('Frozen snapshot files were added or removed')
    for name, value in expected.items():
        if digest(folder / name) != value:
            raise ValueError(f'Frozen snapshot integrity mismatch: {name}')
    canonical = json.dumps(expected, sort_keys=True, separators=(',', ':')).encode()
    if hashlib.sha256(canonical).hexdigest() != index['snapshot_sha256']:
        raise ValueError('Snapshot checksum index is inconsistent')
    return index


def freeze(source, output, reviewed_date):
    from synthesis.evaluate_challenge import load_challenge
    date.fromisoformat(reviewed_date)
    if output.exists():
        raise ValueError('Snapshot destination already exists; choose a new version')
    if output.resolve().is_relative_to(source.resolve()):
        raise ValueError('Snapshot must be outside the source candidate')
    manifest, records, answers, reviews = load_challenge(source)
    if not reviews or any(review['decision'] != 'approved' for review in reviews.values()):
        raise ValueError('Every case needs explicit approval before freezing')
    if any(review.get('proposed_changes') for review in reviews.values()):
        raise ValueError('Resolve proposed changes in a versioned adjudication before freezing')
    source_hashes = {name: digest(source / name) for name in ('manifest.json', 'answer_keys.json', 'review_decisions.json')}
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.freeze-stage-', dir=output.parent) as temp:
        folder = Path(temp) / 'snapshot'
        folder.mkdir()
        (folder / 'cases').mkdir()
        (folder / 'provenance').mkdir()
        for case_id in records:
            shutil.copyfile(source / 'cases' / f'{case_id}.json', folder / 'cases' / f'{case_id}.json')
            answers[case_id]['review_status'] = 'user_approved_workflow_expectations'
            answers[case_id]['approval_provenance'] = reviews[case_id]
        for name in ('manifest.json', 'answer_keys.json'):
            shutil.copyfile(source / name, folder / 'provenance' / ('source_' + name))
        shutil.copyfile(source / 'review_decisions.json', folder / 'review_decisions.json')
        (folder / 'answer_keys.json').write_text(json.dumps(answers, indent=2) + '\n')
        frozen = dict(manifest)
        frozen.update(dataset_id='discharge_workflow_approved_v1', version=1, frozen_date=reviewed_date,
                      frozen=True, frozen_for_tuning=True, approved_for_workflow_regression=True,
                      approved_for_benchmark=False,
                      review_state='All 26 workflow expectations explicitly user-approved; independent clinical validation not established.',
                      purpose='Fixed user-reviewed development/regression expectations before detector changes; not a blinded holdout.',
                      source_candidate=manifest['dataset_id'], source_file_sha256=source_hashes,
                      review_decisions_sha256=digest(folder / 'review_decisions.json'),
                      answer_keys_sha256=digest(folder / 'answer_keys.json'))
        (folder / 'manifest.json').write_text(json.dumps(frozen, indent=2) + '\n')
        (folder / 'README.md').write_text(f'''# Approved workflow regression snapshot v1

Frozen on {reviewed_date} after explicit user approval of all {len(records)} case expectations in chat. The original candidate is preserved separately. The original draft answer key and manifest are retained under provenance/; each approved answer includes its approval provenance. No reviewer name or clinical qualifications have been invented.

This snapshot fixes workflow expectations before implementation changes. These exposed cases are development/regression material, not a blinded holdout or clinically validated benchmark. New task/barrier IDs describe accepted evaluation targets; they do not authorize task execution or imply that production policies implement them.

The patient inputs are byte-for-byte copies of the reviewed candidate. Answer labels, rationales, and approvals remain outside patient inputs. All snapshot files, including the review ledger and approved answers, are hashed in checksums.json. Integrity checks detect drift; these hashes are not digital signatures or filesystem write protection. Do not edit this version in place. Any future adjudication requires a new version.

From the project root:

```sh
python -m synthesis.freeze_challenge --verify data/challenge/discharge_approved_v1
python -m synthesis.evaluate_challenge data/challenge/discharge_approved_v1 --output results/challenge/discharge_approved_v1_baseline
```

The evaluator writes only report files outside this snapshot. It performs no LLM inference, database writes, or production audit writes. The source-file hashes of evaluated components are recorded with the baseline. Narrative and uncertainty requirements remain unassessed by this rule-only runner. Passing ID comparisons do not establish clinical safety or model understanding.
''')
        lines = ['# Approval record', '', f'All {len(reviews)} workflow expectations were explicitly user-approved before this snapshot.', '',
                 '| Case | Review date | Reviewer attribution |', '|---|---|---|']
        for case_id, review in sorted(reviews.items()):
            lines.append(f"| {case_id} | {review['reviewed_at']} | {review['reviewer']} |")
        lines += ['', 'Exact approval statements are retained in review_decisions.json. This records workflow review, not independent clinical credential validation.']
        (folder / 'APPROVAL_RECORD.md').write_text('\n'.join(lines) + '\n')
        files = {str(path.relative_to(folder)): digest(path) for path in sorted(folder.rglob('*')) if path.is_file()}
        canonical = json.dumps(files, sort_keys=True, separators=(',', ':')).encode()
        (folder / 'checksums.json').write_text(json.dumps({'algorithm': 'sha256', 'snapshot_sha256': hashlib.sha256(canonical).hexdigest(), 'files': files}, indent=2) + '\n')
        verify_snapshot(folder)
        load_challenge(folder)
        if any(digest(source / name) != value for name, value in source_hashes.items()):
            raise ValueError('Candidate changed during snapshot creation')
        if output.exists():
            raise ValueError('Destination appeared during snapshot creation')
        folder.rename(output)
    return verify_snapshot(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', nargs='?', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--date', help='Explicit local review/freeze date, YYYY-MM-DD')
    parser.add_argument('--verify', type=Path)
    args = parser.parse_args()
    try:
        if args.verify:
            result = verify_snapshot(args.verify)
        else:
            if not args.source or not args.output or not args.date:
                parser.error('Supply source, --output, and --date, or use --verify')
            result = freeze(args.source, args.output, args.date)
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, f'Snapshot failed: {error}\n')
    print(json.dumps({'verified': True, 'snapshot_sha256': result['snapshot_sha256'], 'files': len(result['files'])}, indent=2))


if __name__ == '__main__':
    main()
