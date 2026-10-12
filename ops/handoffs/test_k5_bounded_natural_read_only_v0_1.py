"""Pure synthetic probe tests; no GitHub, scheduler, SQLite or provider calls."""
import copy
import importlib.util
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

SCRIPT = Path(__file__).with_name('k5_bounded_natural_read_only_v0_1.py')
spec = importlib.util.spec_from_file_location('k5_bounded_probe_test', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
NOW = datetime(2026, 10, 12, 18, 7, tzinfo=timezone.utc)
LAST = NOW.replace(minute=3, second=0)
SYMBOLS = ('BTCUSDT', 'ETHUSDT', 'SOLUSDT')


def fake_deps(root):
    paths = {}
    rows = {}
    fake_markets = {}
    for sym in SYMBOLS:
        rel = f'data/synthetic_{sym}.sqlite'
        (root / 'data').mkdir(exist_ok=True)
        (root / rel).write_bytes(b'SYNTHETIC ONLY')
        paths[sym] = rel
        identity = f"AI-v1.3:{sym}:2026-10-12T18:00:00Z"
        cohort = [
            {'sequence': 1, 'record_hash': f'{sym}-h1', 'entity_id': 'activation', 'record_type': 'ACTIVATION'},
            {'sequence': 2, 'record_hash': f'{sym}-h2', 'entity_id': identity, 'record_type': 'INFERENCE'},
            {'sequence': 3, 'record_hash': f'{sym}-h3', 'entity_id': identity, 'record_type': 'NO_TRADE'},
        ]
        rows[sym] = cohort
        fake_markets[sym] = {
            'ledger_verification': {'valid': True}, 'activation_anchor_match': True,
            'records': 3, 'current_head_hash': cohort[-1]['record_hash'],
            'counts_by_type': dict(Counter(r['record_type'] for r in cohort)),
            'valid_inferences': 1, 'completed_shadow_trades': 0, 'open_signals': 0,
        }
    task = {
        'available': True, 'task_name': module.TASK_NAME, 'state': 'Ready',
        'last_task_result': 0, 'last_run_time': LAST.isoformat(),
        'next_run_time': (NOW + timedelta(minutes=56)).isoformat(),
    }
    gates = {'C1': (100, 20, 0), 'C2': (500, 50, 60), 'C3': (1000, 100, 120)}
    frozen = {'valid': True, 'gates': {
        key: {'valid_inferences': values[0], 'completed_shadow_trades': values[1],
              'minimum_calendar_days': values[2]}
        for key, values in gates.items()
    }}
    report = {
        'runtime_version': 'AI-v1.3', 'program_id': 'crypto-expansion-1', 'mode': 'READ_ONLY',
        'health': {key: True for key in (
            'healthy','ledgers_valid','activation_anchor_matches_ledgers',
            'crypto_artifacts_valid','activation_anchor_upstream_valid',
            'scheduler_healthy','public_signal_exposure_disabled','broker_execution_disabled',
        )},
        'activation': {'public_signal_exposure_enabled': False, 'broker_execution_enabled': False},
        'gates': {key: {
            'valid_inferences': {'required': spec['valid_inferences']},
            'completed_shadow_trades': {'required': spec['completed_shadow_trades']},
            'minimum_calendar_days': spec['minimum_calendar_days'],
        } for key, spec in frozen['gates'].items()},
        'scheduler': {'healthy': True, 'task_name': module.TASK_NAME, 'state': 'Ready',
                      'last_task_result': 0, 'last_run_time': LAST.isoformat()},
        'markets': fake_markets,
        'totals': {'valid_inferences': 3, 'completed_shadow_trades': 0, 'open_shadow_signals': 0},
    }
    def reader(path):
        return copy.deepcopy(rows[next(s for s in SYMBOLS if path.name == Path(paths[s]).name)])
    def verifier(records):
        return {'valid': True, 'records': len(records), 'head_hash': records[-1]['record_hash']}
    return {'root': root, 'now': NOW, 'markets': SYMBOLS, 'database_paths': paths,
            'task_reader': lambda: copy.deepcopy(task), 'record_reader': reader,
            'record_verifier': verifier, 'report_builder': lambda *a, **k: copy.deepcopy(report),
            'gates_reader': lambda root: copy.deepcopy(frozen)}, task, rows, report, frozen


def test_bounded_healthy_completed_cycle_and_private_field_exclusion(tmp_path):
    deps, _, _, _, _ = fake_deps(tmp_path)
    output = module.inspect(**deps)
    assert output['result'] == 'PASS'
    assert output['cycle_close_utc'] == '2026-10-12T18:00:00+00:00'
    assert output['within_publication_15_min_window'] is True
    assert len(output['markets']) == 3
    encoded = json.dumps(output)
    for bad in ('record_hash','entity_id','ledger_path','payload_json', 'source_file', 'provider_payload'):
        assert bad not in encoded


def test_bounded_incomplete_natural_cycle_holds(tmp_path):
    deps, _, rows, _, _ = fake_deps(tmp_path)
    rows['ETHUSDT'][-1]['record_type'] = 'ERROR'
    with pytest.raises(module.VerificationHeld, match='REPORT_COUNTS_DRIFT'):
        module.inspect(**deps)
    # If the report also describes the unsuccessful terminal accurately,
    # the probe must classify it as an incomplete natural cycle, not PASS.
    deps, _, rows, report, _ = fake_deps(tmp_path)
    rows['ETHUSDT'][-1]['record_type'] = 'ERROR'
    report['markets']['ETHUSDT']['counts_by_type'] = {'ACTIVATION':1,'INFERENCE':1,'ERROR':1}
    result=module.inspect(**deps)
    assert result['result']=='HOLD_INCOMPLETE_NATURAL_CYCLE'


def test_stable_valid_new_append_between_two_reads_holds(tmp_path):
    deps, _, rows, _, _ = fake_deps(tmp_path)
    seen = {'BTCUSDT':0}
    reader=deps['record_reader']
    def alternating(path):
        result=reader(path)
        if path.name.endswith('BTCUSDT.sqlite'):
            seen['BTCUSDT'] += 1
            if seen['BTCUSDT'] > 1:
                result.append({'sequence':4,'record_hash':'new-valid-record',
                               'entity_id':'later-cycle','record_type':'EXIT'})
        return result
    deps['record_reader']=alternating
    with pytest.raises(module.VerificationHeld, match='SOURCE_LEDGER_MOVED'):
        module.inspect(**deps)


def test_task_drift_holds(tmp_path):
    deps, task, _, _, _=fake_deps(tmp_path)
    reads={'n':0}
    def task_reader():
        reads['n']+=1
        got=copy.deepcopy(task)
        if reads['n']==2: got['last_run_time']=(LAST + timedelta(hours=1)).isoformat()
        return got
    deps['task_reader']=task_reader
    with pytest.raises(module.VerificationHeld):
        module.inspect(**deps)


def test_unhealthy_report_holds(tmp_path):
    deps, _, _, report, _=fake_deps(tmp_path)
    report['health']['activation_anchor_upstream_valid']=False
    with pytest.raises(module.VerificationHeld, match='SOURCE_REPORT_HEALTH_HELD'):
        module.inspect(**deps)


def test_frozen_gate_mismatch_holds(tmp_path):
    deps, _, _, report, _=fake_deps(tmp_path)
    report['gates']['C2']['valid_inferences']['required']=999
    with pytest.raises(module.VerificationHeld, match='FROZEN_GATE_THRESHOLD_DRIFT'):
        module.inspect(**deps)


def test_age_and_task_type_hold(tmp_path):
    deps, task, _, _, _=fake_deps(tmp_path)
    task['last_task_result'] = True
    with pytest.raises(module.VerificationHeld, match='TASK_NOT_NATURALLY_FINISHED'):
        module.inspect(**deps)
    deps, task, _, _, _=fake_deps(tmp_path)
    task['last_run_time']=(NOW - timedelta(hours=2)).isoformat()
    with pytest.raises(module.VerificationHeld, match='COMPLETED_K5_RUN_NOT_RECENT'):
        module.inspect(**deps)


def test_cli_on_non_windows_fails_closed_with_no_private_data(tmp_path):
    out = subprocess.run([sys.executable, '-B', str(SCRIPT), str(tmp_path)],
                         capture_output=True, text=True, check=False)
    assert out.returncode == 2
    assert '"result": "HELD"' in out.stdout
    assert 'WINDOWS_PYTHON_312_REQUIRED' in out.stdout
    assert out.stderr == ''
