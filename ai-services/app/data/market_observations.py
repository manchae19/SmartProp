"""Append-only, evidence-backed asking-price observations (no model predictions)."""
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import uuid
from statistics import median

VN = timezone(timedelta(hours=7))
APARTMENT = 'Căn hộ chung cư'
MIN_GROUPS = 10  # Planning threshold, not statistical assurance.
MIN_MONTHS = 18  # Admission to future backtesting, never automatic forecast approval.


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(body):
    return hashlib.sha256(body).hexdigest()


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError('observed_at requires an explicit timezone')
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError('observed_at requires an explicit timezone')
    return dt.astimezone(timezone.utc)


def normalize(event):
    event = dict(event)
    if event.get('schema_version') != 1 or event.get('source') != 'cafeland':
        raise ValueError('Unsupported observation schema/source')
    identifier = event.get('source_listing_id', '')
    if not re.fullmatch(r'\d+', identifier) or event.get('record_key') != 'cafeland:' + identifier:
        raise ValueError('Listing identity differs')
    if not re.fullmatch(r'https://nhadat\.cafeland\.vn/[^/?#]+-' + identifier + r'\.html', event.get('detail_url', '')):
        raise ValueError('Unexpected listing URL')
    observed = timestamp(event.get('observed_at'))
    if observed > datetime.now(timezone.utc) + timedelta(minutes=5):
        raise ValueError('Future observation time refused')
    event['observed_at'] = observed.isoformat(timespec='microseconds')
    if event.get('target_type') != 'asking_price' or event.get('training_allowed') is not False:
        raise ValueError('Market observations are not training or AI labels')
    for key in ['response_sha256', 'provenance_sha256']:
        if not re.fullmatch('[a-f0-9]{64}', event.get(key, '')):
            raise ValueError('Missing source/provenance digest')
    if not event.get('property_candidate_group'):
        raise ValueError('Missing reviewed candidate group')
    if not isinstance(event.get('quality_flags'), list) or any(not isinstance(x, str) for x in event['quality_flags']):
        raise ValueError('quality_flags must be an explicit list')
    event['quality_flags'] = sorted(set(event['quality_flags']))
    status, code = event.get('availability'), event.get('http_status')
    if (status, code) not in [('available', 200), ('not_found', 404), ('not_found', 410), ('parse_error', 200)]:
        raise ValueError('Unrecognized HTTP observation; never infer sold')
    for field in ['price_million', 'area_sqm']:
        value = event.get(field)
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0):
            raise ValueError('Invalid ' + field)
        if status != 'available' and value is not None:
            raise ValueError('Unavailable pages must not carry a stale price/area')
    if event.get('quality_eligible') is not False and event.get('quality_eligible') is not True:
        raise ValueError('Explicit quality gate required')
    if event['quality_eligible'] and (status != 'available' or event['quality_flags'] or
            event.get('currency') != 'VND' or event.get('category') != APARTMENT or
            event.get('transaction_type') != 'sale' or not event.get('location_feature') or
            event.get('price_million') is None or event.get('area_sqm') is None):
        raise ValueError('Quality gate contradicts observation')
    if event.get('source_published_date'):
        datetime.strptime(event['source_published_date'], '%Y-%m-%d')
    return event


def persist_evidence(directory, content, suffix):
    """Publish a complete body without replacing an existing evidence file."""
    path = directory / (digest(content) + suffix)
    directory.mkdir(exist_ok=True)
    if path.exists():
        if path.read_bytes() != content:
            raise ValueError('Evidence store changed: ' + path.name)
        return
    temporary = directory / ('.pending_' + uuid.uuid4().hex)
    try:
        with temporary.open('xb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            # Same-directory hard link publishes atomically and refuses to
            # overwrite. A killed writer can only leave an unreferenced temp.
            os.link(temporary, path)
        except FileExistsError:
            if path.read_bytes() != content:
                raise ValueError('Evidence store changed: ' + path.name)
    finally:
        temporary.unlink(missing_ok=True)


class ObservationStore:
    """SQLite transactions serialize writers; evidence is content addressed."""
    def __init__(self, root, *, create=False):
        self.root = Path(root).resolve()
        db = self.root / 'observations.sqlite3'
        if not create and not db.is_file():
            raise FileNotFoundError(db)
        if create:
            self.root.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(db, timeout=10) if create else sqlite3.connect(db.as_uri() + '?mode=ro', uri=True)
        try:
            self.db.execute('PRAGMA foreign_keys=ON')
            version = self.db.execute('PRAGMA user_version').fetchone()[0]
            if version == 0 and create:
                with self.db:
                    self.db.executescript('''
                        BEGIN IMMEDIATE;
                        CREATE TABLE listings (
                            record_key TEXT PRIMARY KEY, source TEXT NOT NULL, source_listing_id TEXT NOT NULL,
                            UNIQUE(source, source_listing_id));
                        CREATE TABLE observations (
                            observation_id TEXT PRIMARY KEY,
                            record_key TEXT NOT NULL REFERENCES listings(record_key),
                            observed_at TEXT NOT NULL, payload TEXT NOT NULL,
                            UNIQUE(record_key, observed_at));
                        CREATE INDEX ix_observation_time ON observations(observed_at, record_key);
                        CREATE TRIGGER listings_no_update BEFORE UPDATE ON listings BEGIN SELECT RAISE(ABORT,'append only'); END;
                        CREATE TRIGGER listings_no_delete BEFORE DELETE ON listings BEGIN SELECT RAISE(ABORT,'append only'); END;
                        CREATE TRIGGER observations_no_update BEFORE UPDATE ON observations BEGIN SELECT RAISE(ABORT,'append only'); END;
                        CREATE TRIGGER observations_no_delete BEFORE DELETE ON observations BEGIN SELECT RAISE(ABORT,'append only'); END;
                        PRAGMA user_version=1;
                        COMMIT;
                    ''')
            elif version != 1:
                raise ValueError('Unsupported observation database version')
        except BaseException:
            self.db.close()
            raise

    def close(self):
        self.db.close()

    def append(self, event, body, provenance):
        event = normalize(event)
        if digest(body) != event['response_sha256'] or digest(provenance) != event['provenance_sha256']:
            raise ValueError('Evidence differs from observation')
        # Write immutable evidence before the transaction; an interrupted append
        # may leave unreferenced evidence but cannot leave a row without a body.
        for content, suffix in [(body, '.html'), (provenance, '.json')]:
            persist_evidence(self.root / 'evidence', content, suffix)
        payload = canonical(event)
        identifier = digest(payload.encode('utf8'))
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO listings VALUES (?,?,?)',
                            (event['record_key'], event['source'], event['source_listing_id']))
            existing = self.db.execute('SELECT observation_id FROM observations WHERE record_key=? AND observed_at=?',
                                       (event['record_key'], event['observed_at'])).fetchone()
            if existing:
                if existing[0] != identifier:
                    raise ValueError('Conflicting observation at identical source ID/time; preserve original')
                return False
            self.db.execute('INSERT INTO observations VALUES (?,?,?,?)',
                            (identifier, event['record_key'], event['observed_at'], payload))
        return True

    def read_verified(self):
        if self.db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok' or self.db.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Observation database failed integrity checks')
        rows = []
        for identifier, key, observed, payload in self.db.execute('SELECT * FROM observations ORDER BY observed_at, record_key'):
            event = normalize(json.loads(payload))
            if digest(payload.encode('utf8')) != identifier or canonical(event) != payload or (event['record_key'], event['observed_at']) != (key, observed):
                raise ValueError('Observation payload changed')
            for field, suffix in [('response_sha256', '.html'), ('provenance_sha256', '.json')]:
                path = self.root / 'evidence' / (event[field] + suffix)
                if digest(path.read_bytes()) != event[field]:
                    raise ValueError('Observation evidence changed: ' + path.name)
            rows.append(dict(event, observation_id=identifier))
        return rows


def month_of(event):
    return timestamp(event['observed_at']).astimezone(VN).strftime('%Y-%m')


def previous_month(month):
    year, number = map(int, month.split('-'))
    return f'{year if number > 1 else year - 1:04d}-{number - 1 if number > 1 else 12:02d}'


def area_band(area):
    if area < 20:
        return 'under20'
    if area < 50:
        return '20-49'
    if area < 80:
        return '50-79'
    if area < 120:
        return '80-119'
    return '120plus'


def monthly_series(events):
    """Latest actual observation in each month; never forward/back fill."""
    latest = {}
    for row in events:
        key = (month_of(row), row['record_key'])
        if key not in latest or timestamp(row['observed_at']) > timestamp(latest[key]['observed_at']):
            latest[key] = row
    groups = defaultdict(list)
    for (month, _), row in latest.items():
        groups[(month, row['property_candidate_group'])].append(row)
    representatives, suppressed = [], Counter()
    for (month, group), members in groups.items():
        # A bad or disappeared member must not be hidden by a good duplicate.
        if any(not r['quality_eligible'] for r in members):
            suppressed['latest_group_member_unavailable_or_unresolved'] += 1
            continue
        conflicting = any(len({r[field] for r in members}) > 1 for field in ['location_feature', 'category'])
        conflicting |= any((max(r[field] for r in members) - min(r[field] for r in members)) / max(r[field] for r in members) > tolerance
                           for field, tolerance in [('price_million', .05), ('area_sqm', .01)])
        if conflicting:
            suppressed['group_values_conflict'] += 1
            continue
        row = max(members, key=lambda r: (timestamp(r['observed_at']), r['record_key']))
        representatives.append(dict(row, month=month, area_band=area_band(row['area_sqm']),
                                    unit_price_million=row['price_million'] / row['area_sqm']))
    cells = defaultdict(list)
    for row in representatives:
        cells[(row['month'], row['location_feature'], row['area_band'])].append(row)
    series = []
    for (month, location, band), members in sorted(cells.items()):
        before = {r['property_candidate_group']: r for r in cells.get((previous_month(month), location, band), [])}
        changes = []
        for row in members:
            old = before.get(row['property_candidate_group'])
            if old and abs(old['area_sqm'] - row['area_sqm']) / max(old['area_sqm'], row['area_sqm']) <= .01:
                changes.append((row['unit_price_million'] / old['unit_price_million'] - 1) * 100)
        series.append(dict(month=month, location_feature=location, area_band=band, groups=len(members),
            sources=','.join(sorted({r['source'] for r in members})),
            median_unit_price_million=median(r['unit_price_million'] for r in members),
            median_total_price_million=median(r['price_million'] for r in members),
            sample_gate_passed=len(members) >= MIN_GROUPS, paired_groups=len(changes),
            paired_median_change_pct=median(changes) if len(changes) >= MIN_GROUPS else None))
    longest = 0
    streaks = {}
    for row in series:
        cell = (row['location_feature'], row['area_band'])
        prior_month, length = streaks.get(cell, (None, 0))
        length = (length + 1 if prior_month == previous_month(row['month']) else 1) if row['sample_gate_passed'] else 0
        streaks[cell] = (row['month'], length)
        longest = max(longest, length)
    counts = Counter(month_of(r) for r in events)
    return series, dict(observations=len(events), listings=len({r['record_key'] for r in events}),
        observations_by_month=dict(sorted(counts.items())),
        observations_by_availability=dict(Counter(r['availability'] for r in events)),
        eligible_observations=sum(r['quality_eligible'] for r in events),
        monthly_candidate_groups=len(representatives), suppressed_group_months=dict(suppressed),
        longest_adequate_month_streak=longest, min_groups_per_cell=MIN_GROUPS,
        min_months_for_backtest_planning=MIN_MONTHS, backtest_history_gate_passed=longest >= MIN_MONTHS,
        forecast_model_trained=False, forecast_published=False,
        semantics='Observed asking prices, Vietnam calendar months, no time filling. Not transactions or a market index.')
