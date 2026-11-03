"""Reconciliation stages a new ledger; source histories and caps stay intact."""
import hashlib,os,sqlite3,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'harness-bench'))
from harness.budget import BudgetGuard,BudgetExceeded
from service import reconcile_budget as reconcile

class BudgetReconciliation(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='cx1-reconcile-test-',dir='/private/tmp'if Path('/private/tmp').is_dir()else None);self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.local=self.root/'local.sqlite3';self.cloud=self.root/'cloud.sqlite3';self.output=self.root/'unapproved-stage.sqlite3';self.config=self.root/'budget.yaml'
        self.config.write_text(f'total_usd: 0.25\nhard_stop_pct: 0.95\nledger: {self.local}\n')
        self.a=BudgetGuard.initialize_ledger(str(self.config))
        self.common=self.a.reserve_chat('muse-spark-1.3',100,100);self.a.settle(self.common,'muse-spark-1.3',{'prompt_tokens':10,'completion_tokens':5})
        with sqlite3.connect(self.local)as source,sqlite3.connect(self.cloud)as target:source.backup(target)
        self.b=BudgetGuard(str(self.config),ledger_path=str(self.cloud))
    def hashes(self):return[hashlib.sha256(p.read_bytes()).hexdigest()for p in(self.local,self.cloud)]
    def test_union_deduplicates_identical_rows_retains_hold_and_does_not_change_sources(self):
        held=self.a.reserve_chat('muse-spark-1.3',100,100);charged=self.b.reserve_chat('muse-spark-1.3',100,100);self.b.settle(charged,'muse-spark-1.3',{'prompt_tokens':12,'completion_tokens':7})
        before=self.hashes();report=reconcile.stage(self.local,self.cloud,self.output)
        self.assertEqual(self.hashes(),before);self.assertEqual(report['shared_rows'],1);self.assertEqual(report['union']['rows'],3);self.assertEqual(report['union']['holds'],1)
        staged=BudgetGuard(str(self.config),ledger_path=str(self.output));status=staged.status();self.assertEqual(status['total_usd'],.25);self.assertEqual(status['stop_usd'],.2375);self.assertEqual(status['calls'],2);self.assertEqual(status['holds'],1)
        with sqlite3.connect(self.output)as c:self.assertEqual(c.execute('SELECT state FROM reservations WHERE id=?',(held,)).fetchone()[0],'HOLD')
        self.assertFalse(report['cloud_freshness_verified']);self.assertFalse(report['deployment_approved'])
    def test_conflicting_shared_reservation_is_rejected_without_a_stage_or_private_echo(self):
        with sqlite3.connect(self.cloud)as c:c.execute('UPDATE reservations SET note=? WHERE id=?',('PRIVATE-DO-NOT-ECHO',self.common))
        with self.assertRaises(reconcile.ReconciliationError)as caught:reconcile.stage(self.local,self.cloud,self.output)
        self.assertNotIn('PRIVATE',str(caught.exception));self.assertFalse(self.output.exists())
    def test_different_allocation_or_lineage_is_rejected_never_combined_or_increased(self):
        for key,value in [('total_micro','300000'),('created_at','2026-01-01T00:00:00+00:00')]:
            with self.subTest(key=key):
                with sqlite3.connect(self.cloud)as c:
                    old=c.execute('SELECT value FROM meta WHERE key=?',(key,)).fetchone()[0];c.execute('UPDATE meta SET value=? WHERE key=?',(value,key))
                with self.assertRaises(reconcile.ReconciliationError):reconcile.stage(self.local,self.cloud,self.output)
                self.assertFalse(self.output.exists())
                with sqlite3.connect(self.cloud)as c:c.execute('UPDATE meta SET value=? WHERE key=?',(old,key))
    def test_blocked_reservation_survives_and_staged_guard_still_refuses_new_spend(self):
        rid=self.b.reserve_chat('muse-spark-1.3',10,10)
        with self.assertRaises(BudgetExceeded):self.b.settle(rid,'muse-spark-1.3',{'prompt_tokens':100000,'completion_tokens':100000})
        report=reconcile.stage(self.local,self.cloud,self.output);self.assertEqual(report['union']['blocked'],1);self.assertTrue(report['budget_blocked'])
        guard=BudgetGuard(str(self.config),ledger_path=str(self.output))
        with self.assertRaises(BudgetExceeded):guard.reserve_chat('muse-spark-1.3',1,1)
    def test_missing_corrupt_or_extended_schema_does_not_create_or_silently_drop_history(self):
        missing=self.root/'missing.sqlite3'
        with self.assertRaises(reconcile.ReconciliationError):reconcile.compare(self.local,missing)
        self.assertFalse(missing.exists());missing.write_bytes(b'not SQLite')
        with self.assertRaises(reconcile.ReconciliationError):reconcile.compare(self.local,missing)
        with sqlite3.connect(self.cloud)as c:c.execute('CREATE TABLE unexpected_history(value TEXT)')
        with self.assertRaises(reconcile.ReconciliationError):reconcile.stage(self.local,self.cloud,self.output)
        self.assertFalse(self.output.exists())
    def test_output_cannot_overwrite_existing_files_sources_or_symlinks(self):
        before=self.hashes();self.output.write_bytes(b'KEEP')
        for output in(self.local,self.cloud,self.output):
            with self.assertRaises(reconcile.ReconciliationError):reconcile.stage(self.local,self.cloud,output)
        alias=self.root/'alias.sqlite3';alias.symlink_to(self.local)
        with self.assertRaises(reconcile.ReconciliationError):reconcile.stage(self.local,self.cloud,alias)
        self.assertEqual(self.hashes(),before);self.assertEqual(self.output.read_bytes(),b'KEEP')
    def test_invalid_amounts_or_pending_state_are_not_accepted_as_a_clean_history(self):
        for change in ["settled_micro=-1","state='HOLD'","settled_micro=reserved_micro+1"]:
            with self.subTest(change=change):
                with sqlite3.connect(self.cloud)as c:c.execute('SAVEPOINT fixture');c.execute('UPDATE reservations SET '+change);c.commit()
                with self.assertRaises(reconcile.ReconciliationError):reconcile.compare(self.local,self.cloud)
                with sqlite3.connect(self.local)as source,sqlite3.connect(self.cloud)as target:source.backup(target)
    def test_sources_changed_while_staging_prevent_a_success_receipt(self):
        original=reconcile._write_stage
        def concurrent_write(*args):
            identity=original(*args);self.a.reserve_chat('muse-spark-1.3',1,1);return identity
        with patch.object(reconcile,'_write_stage',side_effect=concurrent_write):
            with self.assertRaises(reconcile.ReconciliationError):reconcile.stage(self.local,self.cloud,self.output)
    def test_a_path_swap_cannot_redirect_writes_into_a_source_or_get_a_success_receipt(self):
        before=self.hashes();real_open=os.open;swaps=[]
        def swapped(path,flags,mode=0o777):
            fd=real_open(path,flags,mode)
            if flags&os.O_EXCL:Path(path).unlink();Path(path).symlink_to(self.local);swaps.append(path)
            return fd
        with patch.object(reconcile.os,'open',side_effect=swapped):
            with self.assertRaises(reconcile.ReconciliationError):reconcile.stage(self.local,self.cloud,self.output)
        self.assertEqual(self.hashes(),before);self.assertEqual(swaps,[self.output]);self.assertTrue(self.output.is_symlink())
    def test_union_above_stop_preserves_the_cap_and_never_becomes_deployment_approval(self):
        local=self.root/'small-local.sqlite3';cloud=self.root/'small-cloud.sqlite3';config=self.root/'small.yaml';config.write_text(f'total_usd: 0.0001\nhard_stop_pct: 0.95\nledger: {local}\n')
        a=BudgetGuard.initialize_ledger(str(config))
        with sqlite3.connect(local)as source,sqlite3.connect(cloud)as target:source.backup(target)
        b=BudgetGuard(str(config),ledger_path=str(cloud))
        for guard in(a,b):guard.charge_tokens('muse-spark-1.3',{'prompt_tokens':48,'completion_tokens':0})
        report=reconcile.stage(local,cloud,self.output);self.assertEqual(report['total_micro'],100);self.assertEqual(report['stop_micro'],95);self.assertEqual(report['union']['committed_micro'],120);self.assertEqual(report['remaining_to_stop_micro'],0);self.assertTrue(report['budget_blocked']);self.assertFalse(report['deployment_approved'])
        guard=BudgetGuard(str(config),ledger_path=str(self.output))
        with self.assertRaises(BudgetExceeded):guard.reserve_chat('muse-spark-1.3',1,1)
    def test_output_swapped_during_final_source_check_never_gets_a_success_receipt(self):
        original=reconcile.read_snapshot;local_reads=0
        def swap_during_source_check(path):
            nonlocal local_reads
            if Path(path)==self.local:
                local_reads+=1
                if local_reads==2:self.output.unlink();self.output.symlink_to(self.local)
            return original(path)
        before=self.hashes()
        with patch.object(reconcile,'read_snapshot',side_effect=swap_during_source_check):
            with self.assertRaises(reconcile.ReconciliationError):reconcile.stage(self.local,self.cloud,self.output)
        self.assertEqual(self.hashes(),before)
    def test_wal_snapshot_without_shm_is_rejected_without_creating_coordination_files(self):
        active=self.root/'active.sqlite3';snapshot=self.root/'wal-snapshot.sqlite3'
        with sqlite3.connect(self.cloud)as source,sqlite3.connect(active)as target:source.backup(target)
        writer=sqlite3.connect(active)
        try:
            writer.execute('PRAGMA journal_mode=WAL');writer.execute('PRAGMA wal_autocheckpoint=0');writer.execute("UPDATE reservations SET note='WAL-only change'");writer.commit()
            snapshot.write_bytes(active.read_bytes());Path(str(snapshot)+'-wal').write_bytes(Path(str(active)+'-wal').read_bytes())
            before={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in self.root.glob('wal-snapshot*')}
            self.assertFalse(Path(str(snapshot)+'-shm').exists())
            with self.assertRaises(reconcile.ReconciliationError):reconcile.read_snapshot(snapshot)
            self.assertFalse(Path(str(snapshot)+'-shm').exists());self.assertEqual(before,{p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in self.root.glob('wal-snapshot*')})
        finally:writer.close()
    def test_in_place_stage_change_during_source_check_never_gets_a_success_receipt(self):
        original=reconcile.read_snapshot;local_reads=0
        def change_stage_during_source_check(path):
            nonlocal local_reads
            if Path(path)==self.local:
                local_reads+=1
                if local_reads==2:
                    with sqlite3.connect(self.output)as c:c.execute("UPDATE reservations SET note='Changed stage'")
            return original(path)
        before=self.hashes()
        with patch.object(reconcile,'read_snapshot',side_effect=change_stage_during_source_check):
            with self.assertRaises(reconcile.ReconciliationError):reconcile.stage(self.local,self.cloud,self.output)
        self.assertEqual(self.hashes(),before)
