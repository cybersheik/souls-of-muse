"""One-time writer-permit seeding (operator only, explicit --confirm).

Seeds exactly one permit into the named Modal Queue som-writer-permit.
This is a one-time operator action; it creates no other resources or
permissions automatically.

Durable one-time marker: before any queue write, a marker file is
stored on the named Volume som-data and committed. If the marker
already exists, seeding is refused even if the queue is empty — an
empty queue can also mean a running container currently holds the
permit, so ``q.len() == 0`` alone must never authorise a second
writer. The queue-length check is kept as a second refusal.

Order on a first seed is marker-create-and-commit BEFORE q.put.
If seeding crashes after the marker commit but before q.put, the
next run will refuse (marker present, queue empty): that state
requires explicit operator reconciliation. There is no
auto-recovery and no automatic marker/queue reset in this script.
Requires Modal auth (operator action-time permission). No secrets here.
Author: Meta Muse Wonder.
"""
import argparse

MARKER_PATH = "writer-permit.seeded"
QUEUE_NAME = "som-writer-permit"
VOLUME_NAME = "som-data"
PERMIT_VALUE = "writer-permit"


class SeedRefused(RuntimeError):
    """Seeding would create a second writer; refusing."""


def seed_once(queue, marker_store):
    """Seed one permit, guarded by the durable volume marker.

    Injected for offline testing. ``queue`` provides ``len()`` and
    ``put(value)``; ``marker_store`` provides ``exists()`` and
    ``create_and_commit()`` (write marker on som-data, then commit).

    Refuses (SeedRefused) if the marker already exists (even with
    an empty/held queue) or if the queue is already non-empty.
    On success the order is exactly: marker create+commit, then put.
    """
    if marker_store.exists():
        raise SeedRefused(
            "durable seed marker already exists on volume som-data; "
            "refusing to seed another permit (if a previous seed crashed "
            "after the marker but before the queue put, explicit operator "
            "reconciliation is required; no auto-recovery/reset is performed)"
        )
    n = queue.len()
    if n != 0:
        raise SeedRefused(f"queue already holds {n} item(s); refusing to seed another permit")
    marker_store.create_and_commit()
    queue.put(PERMIT_VALUE)
    return {"seeded": True, "queue_len": queue.len()}


class _ModalVolumeMarkerStore:
    """Real marker store backed by the named Modal Volume som-data."""

    def __init__(self, volume):
        self._volume = volume

    def exists(self):
        try:
            entries = self._volume.listdir("/")
        except Exception:
            return False
        for entry in entries:
            path = getattr(entry, "path", None) or getattr(entry, "name", None) or str(entry)
            if str(path).rstrip("/").endswith(MARKER_PATH):
                return True
        return False

    def create_and_commit(self):
        import io
        # batch_upload commits the marker to the volume on exit,
        # before the caller puts the queue permit.
        with self._volume.batch_upload(force=False) as batch:
            batch.put_file(io.BytesIO(b"writer-permit seeded (one-time)\n"), MARKER_PATH)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm", action="store_true", help="required: confirms one-time seeding")
    a = ap.parse_args()
    if not a.confirm:
        ap.error("--confirm is required; seeding is a one-time explicit operator action")
    import modal
    q = modal.Queue.from_name(QUEUE_NAME, create_if_missing=False)
    vol = modal.Volume.from_name(VOLUME_NAME, create_if_missing=False, version=2)
    marker = _ModalVolumeMarkerStore(vol)
    try:
        result = seed_once(q, marker)
    except SeedRefused as exc:
        raise SystemExit(str(exc)) from exc
    print(result)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
