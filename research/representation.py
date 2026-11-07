"""Small trainable contrastive encoder. No labels, IDs or narrative text are features."""
import hashlib
import math
import random
from research.provenance import digest

FEATURE_FIELDS = (
    'medical_stability_status', 'medication_reconciliation_status', 'medication_education_status',
    'medication_availability', 'patient_education_status', 'diet_education_status',
    'mobility_device_education_status', 'medical_device_education_status', 'followup_status',
    'caregiver_status', 'transport_status', 'planned_discharge_window', 'financial_status',
    'case_manager_status', 'home_safety_status', 'outpatient_therapy_status', 'pcp_notification_status',
    'physical_function', 'discharge_summary_status', 'pending_labs', 'pending_imaging', 'pending_consult')


def features(record):
    tokens = []
    for field in FEATURE_FIELDS:
        value = record.get(field)
        if isinstance(value, list): value = 'present' if value else 'empty'
        if value is None: value = 'missing'
        if isinstance(value, (str, bool, int, float)):
            tokens.append(f'{field}={value}')
        else:
            tokens.append(f'{field}=malformed')
    time = record.get('transport_time')
    tokens.append('transport_hour=' + (time[:2] if isinstance(time, str) and len(time)==5 else 'missing_or_invalid'))
    return tokens


def group_id(record):
    return digest(features(record))


class ContrastiveEncoder:
    def __init__(self, dimensions=12, seed=42):
        if dimensions < 2 or dimensions > 128: raise ValueError('dimensions must be 2..128')
        self.dimensions, self.seed = dimensions, seed
        self.vocabulary, self.weights = [], []
        self.metadata = {}

    def _vector(self, tokens):
        indices = {token: i for i, token in enumerate(self.vocabulary)}
        selected = [indices[t] for t in tokens if t in indices]
        scale = 1 / max(1, len(selected)) ** .5
        return [sum(self.weights[i][j] for i in selected) * scale for j in range(self.dimensions)]

    def fit(self, records, epochs=20, learning_rate=.04):
        if len(records) < 2: raise ValueError('At least two training records are required')
        if epochs < 1 or epochs > 1000: raise ValueError('epochs must be 1..1000')
        if not math.isfinite(learning_rate) or not 0 < learning_rate <= 1: raise ValueError('Invalid learning rate')
        views = [features(r) for r in records]
        if len({digest(v) for v in views}) < 2: raise ValueError('Training requires distinct feature groups')
        self.vocabulary = sorted({t for v in views for t in v})
        rng = random.Random(self.seed)
        self.weights = [[rng.gauss(0, .2) for _ in range(self.dimensions)] for _ in self.vocabulary]
        indices = {t: i for i, t in enumerate(self.vocabulary)}
        losses = []
        def update(a, b, positive):
            za, zb = self._vector(a), self._vector(b)
            delta = [x-y for x, y in zip(za, zb)]
            distance = max(1e-9, math.sqrt(sum(x*x for x in delta)))
            loss = distance**2 if positive else max(0, 1-distance)**2
            factor = 2 if positive else (-2*(1-distance)/distance if distance < 1 else 0)
            coeff = {}
            for tokens, sign in ((a, 1), (b, -1)):
                scale = sign / max(1, len(tokens))**.5
                for token in tokens:
                    i = indices[token]
                    coeff[i] = coeff.get(i, 0) + scale
            for i, c in coeff.items():
                for j in range(self.dimensions):
                    self.weights[i][j] -= learning_rate * (factor * delta[j] * c + .0001*self.weights[i][j])
            return loss
        for _ in range(epochs):
            loss = 0
            order = list(range(len(views)))
            rng.shuffle(order)
            for i in order:
                a = [t for t in views[i] if rng.random() > .15] or views[i][:1]
                b = [t for t in views[i] if rng.random() > .15] or views[i][:1]
                loss += update(a, b, True)
                candidates = [j for j in range(len(views)) if views[j] != views[i]]
                j = rng.choice(candidates)
                loss += update(views[i], views[j], False)
            losses.append(loss/(2*len(views)))
        self.metadata = {'method': 'linear_contrastive_margin', 'seed': self.seed, 'epochs': epochs,
                         'learning_rate': learning_rate, 'dimensions': self.dimensions,
                         'training_records': len(records), 'training_groups': sorted({group_id(r) for r in records}),
                         'training_features_sha256': digest(views), 'loss_by_epoch': losses,
                         'augmentation': 'independent_field_token_dropout_0.15',
                         'labels_used_in_training': False,
                         'limitations': 'Synthetic structured-status representations; no image encoder, pretrained semantics or clinical validation.'}
        return self

    def encode(self, record):
        if not self.weights: raise ValueError('Encoder must be trained first')
        z = self._vector(features(record))
        norm = math.sqrt(sum(v*v for v in z))
        return [v/norm if norm else 0 for v in z]

    def nearest(self, record, references, k=3):
        z = self.encode(record)
        rows = []
        for ref in references:
            vector = self.encode(ref)
            rows.append({'case_id': ref.get('case_id', 'unknown'),
                         'similarity': sum(a*b for a, b in zip(z, vector)), 'group_id': group_id(ref)})
        return sorted(rows, key=lambda r: (-r['similarity'], r['case_id']))[:max(0, k)]

    def artifact(self):
        return {'schema_version': 'contrastive-v1', 'dimensions': self.dimensions,
                'seed': self.seed, 'vocabulary': self.vocabulary, 'weights': self.weights, 'metadata': self.metadata}

    @classmethod
    def from_artifact(cls, artifact):
        if artifact.get('schema_version') != 'contrastive-v1': raise ValueError('Unsupported encoder format')
        model = cls(artifact['dimensions'], artifact['seed'])
        vocabulary, weights = artifact['vocabulary'], artifact['weights']
        if (len(vocabulary) != len(weights) or len(set(vocabulary)) != len(vocabulary)
                or not all(isinstance(t, str) for t in vocabulary)
                or any(len(row) != model.dimensions or any(not isinstance(v, (int,float)) or not math.isfinite(v) for v in row) for row in weights)):
            raise ValueError('Invalid encoder weights')
        model.vocabulary, model.weights, model.metadata = vocabulary, weights, artifact['metadata']
        return model


def split_groups(records, seed=42):
    groups = sorted({group_id(r) for r in records})
    if len(groups) < 3: raise ValueError('At least three distinct feature groups required for train/validation/test')
    random.Random(seed).shuffle(groups)
    n = len(groups)
    ntrain = max(1, min(n-2, int(n*.6)))
    nval = max(1, int(n*.2))
    assignments = {g: ('train' if i < ntrain else 'validation' if i < ntrain+nval else 'test') for i, g in enumerate(groups)}
    return {split: [r for r in records if assignments[group_id(r)] == split] for split in ('train','validation','test')}
