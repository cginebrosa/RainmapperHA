from pathlib import Path
import tempfile
import unittest

from rainmapper_core import mushroom_competing_control as c


class ControlTests(unittest.TestCase):
    def test_costs_are_normalized_deduplicated_and_bounded(self):
        self.assertEqual(c.normalize_ks([4, 2.5, 4.0, 0]), [0.0, 2.5, 4.0])
        for values in ([], [True], [-1], [1001], ['4'], [float('nan')], list(range(9))):
            with self.subTest(values=values), self.assertRaises(ValueError):
                c.normalize_ks(values)

    def test_missing_cost_is_pending_even_with_the_same_control_revision(self):
        self.assertTrue(c.needs_job({'desired_revision':'a'*64, 'active_revision':'a'*64,
                                     'job_id':'', 'pending_ks':[2.5]}))

    def test_delivery_retry_after_publication_does_not_publish_again_or_accept_changed_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'state.json'
            state = c.observe(path, {'observations':'a'*64})
            c.attach_job(path, job_id='worker_job_12345678', expected_revision=state['desired_revision'])
            published = []
            arguments = dict(job_id='worker_job_12345678', result_revision=state['desired_revision'],
                             seconds=2, receipt_sha256='b'*64, publish=lambda:published.append(True))
            first = c.finish(path, **arguments)
            self.assertEqual(c.finish(path, **arguments), first)
            self.assertEqual(published, [True])
            with self.assertRaisesRegex(ValueError, 'identity'):
                c.finish(path, **{**arguments, 'receipt_sha256':'c'*64})

    def test_job_uses_background_slot_and_rejects_duplicate_or_foreign_receipt(self):
        from rainmapper_core import mushroom_worker_jobs as jobs
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'jobs.json'
            job_id = 'worker_job_history123'
            common = dict(worker_id='worker_aaaaaaaa', worker_display_name='Worker', job_id=job_id,
                          revision='a'*64, input_bundle={'job_id':job_id,
                          'snapshot_id':'sha256:'+'b'*64, 'job_spec_id':'sha256:'+'c'*64})
            job = jobs.create_competing_history_job(path, **common)
            self.assertFalse(job['promotion_eligible'])
            self.assertIsNone(jobs.claim_next(path, worker_id='worker_aaaaaaaa', lane='foreground'))
            with self.assertRaises(jobs.DuplicateActiveWorkError):
                jobs.create_competing_history_job(path, **common)
            claimed = jobs.claim_next(path, worker_id='worker_aaaaaaaa', lane='background')
            auth = dict(job_id=job_id, worker_id='worker_aaaaaaaa', claim_token=claimed['claim_token'])
            jobs.start_job(path, **auth)
            self.assertEqual(jobs.authorize_input_download(path, **auth)['job_id'], job_id)
            with self.assertRaisesRegex(ValueError, 'receipt'):
                jobs.finish_job(path, **auth, status='complete', result={
                    'revision':'d'*64, 'artifact_sha256':'f'*64, 'seconds':1})
            finished = jobs.finish_job(path, **auth, status='failed', error='cancelled before receipt')
            self.assertEqual(finished['status'], 'failed')

    def test_unchanged_inputs_do_not_queue_and_changed_inputs_cannot_publish_stale_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'state.json'
            first = c.observe(path, {'observations': 'a' * 64, 'models': 'b' * 64})
            old = first['desired_revision']
            c.attach_job(path, job_id='worker_job_12345678', expected_revision=old)
            self.assertFalse(c.needs_job(c.observe(path, first['dependencies'])))
            with self.assertRaisesRegex(ValueError, 'duplicate'):
                c.attach_job(path, job_id='worker_job_abcdefgh', expected_revision=old)
            c.observe(path, {'observations': 'c' * 64, 'models': 'b' * 64})
            published = []
            stale = c.finish(path, job_id='worker_job_12345678', result_revision=old,
                             seconds=5, publish=lambda: published.append(True))
            self.assertEqual(published, [])
            self.assertEqual(stale['active_revision'], '')
            self.assertTrue(c.needs_job(stale))
            current = stale['desired_revision']
            c.attach_job(path, job_id='worker_job_abcdefgh', expected_revision=current)
            good = c.finish(path, job_id='worker_job_abcdefgh', result_revision=current,
                            seconds=2.5, publish=lambda: published.append(True))
            self.assertEqual(published, [True])
            self.assertFalse(c.needs_job(good))
            self.assertEqual(c.observe(path, good['dependencies']), good)

    def test_failure_preserves_last_result_and_does_not_claim_freshness(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'state.json'
            first = c.observe(path, {'observations': 'a' * 64})
            rev = first['desired_revision']
            c.attach_job(path, job_id='worker_job_12345678', expected_revision=rev)
            c.finish(path, job_id='worker_job_12345678', result_revision=rev, seconds=1, publish=lambda: None)
            second = c.observe(path, {'observations': 'b' * 64})
            c.attach_job(path, job_id='worker_job_abcdefgh', expected_revision=second['desired_revision'])
            failure = c.finish(path, job_id='worker_job_abcdefgh', result_revision=second['desired_revision'],
                               seconds=3, error='cancelled')
            self.assertEqual(failure['active_revision'], rev)
            self.assertEqual(failure['status'], 'failed')
            self.assertTrue(c.needs_job(failure))

    def test_only_verified_result_for_claimed_revision_can_be_published(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'state.json'
            state = c.observe(path, {'observations': 'a' * 64})
            c.attach_job(path, job_id='worker_job_12345678', expected_revision=state['desired_revision'])
            with self.assertRaisesRegex(ValueError, 'not_verified'):
                c.finish(path, job_id='worker_job_12345678', result_revision=state['desired_revision'], seconds=1)
            self.assertEqual(c.load(path)['active_revision'], '')


if __name__ == '__main__':
    unittest.main()
