"""Synthetic live-card regressions; saved action receipts stay immutable."""
import json

from minecraft_agent.v2.progress import Progress, render
from minecraft_agent.v3.store import Store


def test_new_command_clears_only_preview_and_complete_keeps_real_step_states():
    db = Store(':memory:')
    try:
        task = db.create_task('sandbox', 'dm:200', '100', '200', 'Inspect', 'observe', {'steps': ['Read', 'Verify']})
        progress = Progress(db, [])
        progress.start(task)
        progress.event(task, 'command', 'read initial')
        progress.event(task, 'log', 'old output')
        progress.event(task, 'command', 'fetch next')
        row = db.one('SELECT * FROM kei_progress WHERE task=?', (task,))
        assert row['command'] == 'fetch next' and row['log'] == ''
        before = json.loads(row['steps'])
        progress.complete(task)
        assert json.loads(db.one('SELECT steps FROM kei_progress WHERE task=?', (task,))['steps']) == before
        db.update_task(task, status='succeeded', result='Actual saved final summary')
        payload = render(db.one('SELECT * FROM kei_tasks WHERE id=?', (task,)), row, 'minimal')
        assert 'Actual saved final summary' in payload['embed']['description']
    finally:
        db.db.close()
