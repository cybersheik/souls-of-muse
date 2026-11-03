"""Compare two budget snapshots and optionally stage a NEW private ledger.

No network, provisioning, spend, cap changes, source writes or upload. A stage
is never proof of fresh cloud history or approval to replace the live ledger.
Conflicting shared rows/metadata require operator review, never a winner rule.
"""
import argparse,hashlib,json,os,sqlite3,stat
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

class ReconciliationError(RuntimeError):
    pass

COLUMNS=('id','model','kind','reserved_micro','settled_micro','state','created_at','settled_at','note')
META_KEYS={'schema_version','total_micro','stop_micro','created_at'}
SCHEMA="""
CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE reservations(id TEXT PRIMARY KEY,model TEXT NOT NULL,kind TEXT NOT NULL,
 reserved_micro INTEGER NOT NULL CHECK(reserved_micro>=0),settled_micro INTEGER,
 state TEXT NOT NULL CHECK(state IN ('HOLD','SETTLED','BLOCKED')),
 created_at TEXT NOT NULL,settled_at TEXT,note TEXT);
"""

def _canonical(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
def _sha(value):return hashlib.sha256(_canonical(value)).hexdigest()
def _time(value):
    if not isinstance(value,str):raise ValueError()
    parsed=datetime.fromisoformat(value)
    if parsed.tzinfo is None:raise ValueError()
    return parsed

@dataclass(frozen=True)
class Snapshot:
    metadata:tuple
    rows:tuple
    @property
    def fingerprint(self):return _sha([self.metadata,self.rows])

def _version(info):
    return info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns

def _read_file(path,expected_identity=None):
    """Read a quiescent rollback snapshot without SQLite touching the source.

    Even mode=ro SQLite may create a WAL -shm file. Reject WAL/sidecars rather
    than ignoring their charges. Validate an OS descriptor and file version.
    """
    path=Path(path)
    def no_sidecars():
        if any(os.path.lexists(str(path)+suffix)for suffix in('-wal','-shm','-journal')):raise ValueError()
    before=path.lstat()
    if not stat.S_ISREG(before.st_mode):raise ValueError()
    if expected_identity is not None and(before.st_dev,before.st_ino)!=expected_identity:raise ValueError()
    no_sidecars()
    fd=os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0))
    with os.fdopen(fd,'rb')as f:
        opened=os.fstat(f.fileno())
        if _version(opened)!=_version(before):raise ValueError()
        content=f.read();after=os.fstat(f.fileno())
    current=path.lstat();no_sidecars()
    if not stat.S_ISREG(current.st_mode)or _version(before)!=_version(after)or _version(after)!=_version(current):raise ValueError()
    if len(content)!=before.st_size or len(content)<100 or content[:16]!=b'SQLite format 3\0'or content[18:20]!=b'\x01\x01':raise ValueError()
    return content,_version(current)

def _parse_snapshot(content):
    with closing(sqlite3.connect(':memory:'))as c:
        c.deserialize(content)
        c.execute('PRAGMA query_only=ON');c.execute('PRAGMA trusted_schema=OFF');c.execute('BEGIN')
        if c.execute('PRAGMA quick_check').fetchall()!=[('ok',)]:raise ValueError()
        objects=c.execute("SELECT type,name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'").fetchall()
        if {name for kind,name in objects if kind=='table'}!={'meta','reservations'}:raise ValueError()
        if any(kind not in ('table','index')for kind,name in objects):raise ValueError()
        if tuple(r[1]for r in c.execute('PRAGMA table_info(meta)'))!=('key','value'):raise ValueError()
        if tuple(r[1]for r in c.execute('PRAGMA table_info(reservations)'))!=COLUMNS:raise ValueError()
        metadata=tuple(sorted(c.execute('SELECT key,value FROM meta').fetchall()))
        meta=dict(metadata)
        if len(meta)!=len(metadata)or set(meta)!=META_KEYS or any(not isinstance(v,str)for v in meta.values()):raise ValueError()
        total,stop=int(meta['total_micro']),int(meta['stop_micro'])
        if meta['schema_version']!='1'or not 0<=stop<=total<=2**63-1:raise ValueError()
        _time(meta['created_at'])
        rows=tuple(c.execute('SELECT '+','.join(COLUMNS)+' FROM reservations ORDER BY id').fetchall())
        if len({r[0]for r in rows})!=len(rows):raise ValueError()
        for row in rows:
            rid,model,kind,reserved,settled,state,created,at,note=row
            if any(not isinstance(v,str)or not v for v in (rid,model,kind,state)):raise ValueError()
            if kind not in ('chat','asr')or state not in ('HOLD','SETTLED','BLOCKED'):raise ValueError()
            if type(reserved)is not int or not 0<=reserved<=2**63-1:raise ValueError()
            created_time=_time(created)
            if state=='SETTLED':
                if type(settled)is not int or not 0<=settled<=reserved or _time(at)<created_time:raise ValueError()
            elif settled is not None or at is not None:raise ValueError()
            if note is not None and not isinstance(note,str):raise ValueError()
        snapshot=Snapshot(metadata,rows)
        snapshot.fingerprint
        return snapshot

def read_snapshot(path):
    """Only read descriptors; never SQLite-open a source or create sidecars."""
    try:
        content,_=_read_file(Path(path).resolve(strict=True))
        return _parse_snapshot(content)
    except (OSError,sqlite3.Error,ValueError,TypeError,OverflowError,AttributeError):
        raise ReconciliationError('source is missing, changing, invalid or not a quiescent rollback snapshot')from None

def _amounts(snapshot):
    by_state={state:[r for r in snapshot.rows if r[5]==state]for state in ('SETTLED','HOLD','BLOCKED')}
    settled=sum(r[4]for r in by_state['SETTLED']);held=sum(r[3]for r in by_state['HOLD']);blocked=sum(r[3]for r in by_state['BLOCKED'])
    return {'rows':len(snapshot.rows),'settled':len(by_state['SETTLED']),'holds':len(by_state['HOLD']),
            'blocked':len(by_state['BLOCKED']),'settled_micro':settled,'held_micro':held,
            'blocked_micro':blocked,'committed_micro':settled+held+blocked}

def _plan(local,cloud):
    if local.metadata!=cloud.metadata:
        raise ReconciliationError('allocation or ledger lineage differs; operator review required')
    a={r[0]:r for r in local.rows};b={r[0]:r for r in cloud.rows};shared=a.keys()&b.keys()
    if any(a[rid]!=b[rid]for rid in shared):
        raise ReconciliationError('shared reservation history diverges; operator review required')
    combined={**a,**b};union=Snapshot(local.metadata,tuple(combined[rid]for rid in sorted(combined)))
    meta=dict(union.metadata);amounts=_amounts(union);stop=int(meta['stop_micro'])
    report={'scope':'offline snapshot reconciliation only','schema_version':'1',
        'local_snapshot_sha256':local.fingerprint,'cloud_snapshot_sha256':cloud.fingerprint,
        'union_snapshot_sha256':union.fingerprint,'shared_rows':len(shared),
        'local_only_rows':len(a.keys()-b.keys()),'cloud_only_rows':len(b.keys()-a.keys()),
        'local':_amounts(local),'cloud':_amounts(cloud),'union':amounts,
        'total_micro':int(meta['total_micro']),'stop_micro':stop,
        'remaining_to_stop_micro':max(0,stop-amounts['committed_micro']),
        'budget_blocked':bool(amounts['blocked']or amounts['committed_micro']>=stop),
        'unsettled_requires_review':bool(amounts['holds']or amounts['blocked']),
        'source_databases_modified':False,'allocation_modified':False,
        'cloud_freshness_verified':False,'deployment_approved':False}
    return union,report

def compare(local_path,cloud_path):
    _,report=_plan(read_snapshot(local_path),read_snapshot(cloud_path))
    return report

def _write_stage(output,snapshot):
    # SQLite writes only in memory. Then write through the exclusively created
    # descriptor, so a swapped pathname cannot redirect SQLite into a source.
    try:
        with closing(sqlite3.connect(':memory:'))as c:
            c.executescript(SCHEMA);c.execute('BEGIN IMMEDIATE')
            c.executemany('INSERT INTO meta VALUES(?,?)',snapshot.metadata)
            c.executemany('INSERT INTO reservations VALUES(?,?,?,?,?,?,?,?,?)',snapshot.rows)
            c.commit();content=c.serialize()
    except (sqlite3.Error,AttributeError):
        raise ReconciliationError('could not construct the offline stage')from None
    # O_EXCL refuses existing files AND symlinks. Never open a source for writes.
    try:fd=os.open(output,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    except OSError:raise ReconciliationError('stage path must name a new file in an existing private directory')from None
    try:
        with os.fdopen(fd,'wb')as f:
            info=os.fstat(f.fileno());f.write(content);f.flush();os.fsync(f.fileno())
        return info.st_dev,info.st_ino
    except OSError:
        # An incomplete stage is retained for inspection, never uploaded or
        # overwritten. A failed command produces no success receipt.
        raise ReconciliationError('staging failed; any output is unapproved and requires inspection')from None

def stage(local_path,cloud_path,output_path):
    local=read_snapshot(local_path);cloud=read_snapshot(cloud_path);union,report=_plan(local,cloud)
    output=Path(output_path)
    if output.resolve()in(Path(local_path).resolve(),Path(cloud_path).resolve()):
        raise ReconciliationError('a source ledger cannot be the stage destination')
    identity=_write_stage(output,union)
    try:
        content,version=_read_file(output,identity)
        if _parse_snapshot(content)!=union:raise ValueError()
    except (OSError,sqlite3.Error,ValueError,TypeError,OverflowError,AttributeError):
        raise ReconciliationError('stage verification failed; no verified stage receipt')from None
    if read_snapshot(local_path)!=local or read_snapshot(cloud_path)!=cloud:
        raise ReconciliationError('source changed during staging; output remains unapproved')
    try:
        current=output.lstat()
        if not stat.S_ISREG(current.st_mode)or _version(current)!=version:raise ValueError()
    except (OSError,ValueError):
        raise ReconciliationError('stage file version or pathname changed; no verified stage receipt')from None
    return {**report,'staged_snapshot_verified':True}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--local',required=True,type=Path);parser.add_argument('--cloud',required=True,type=Path)
    parser.add_argument('--stage',type=Path,help='Optional NEW offline ledger; never an existing source/live ledger')
    args=parser.parse_args()
    try:report=stage(args.local,args.cloud,args.stage)if args.stage else compare(args.local,args.cloud)
    except ReconciliationError as exc:parser.exit(2,str(exc)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
