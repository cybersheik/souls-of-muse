"""Modal deployment entrypoint.

CPU only, single serialized writer. Modal Volume + SQLite means one
container must own writes. Single-writer ownership does NOT rely on
max_containers=1 alone: a named Modal Queue (som-writer-permit) holds
exactly one non-refilling writer permit, seeded ONCE by the operator
during first provisioning. Each container must acquire the permit
before Volume.reload() and before opening SQLite; there is no
automatic refill and no TTL recovery. On graceful shutdown the volume
commit must succeed before the permit is returned. A crash therefore
fails closed and requires operator reconciliation/recovery (inspect
state, then re-seed exactly one permit) — this is a deliberately
limited pilot, not production scaling and not a distributed lock.
Region: placement is unpinned (no region argument); verify the actual
region after deploy. Do not claim a region surcharge saving.
Author: Meta Muse Wonder.

Optional MMS inference is isolated in a private CPU worker without the state
Volume, writer Queue or Secrets. Its failure has no writer authority.

Writer-permit release uses the ASGI lifespan shutdown, NOT process-exit handlers:
an ASGI container lifecycle / SIGTERM does not guarantee that Python
process-exit handlers run, so relying on them could leave the permit held forever
after scaledown (next cold start permanently blocked). The lifespan
wrapper below preserves the inner app's original lifespan, and on
lifespan shutdown it commits the volume BEFORE returning the permit,
exactly once. On a failed commit it never releases the permit. If
factory startup fails after the permit was acquired (reload / DB /
create_app), startup fails closed: the permit is intentionally NOT
returned and operator reconciliation is required.
"""
import os
import re
import modal

app = modal.App("souls-of-muse-harness")
volume = modal.Volume.from_name("som-data", create_if_missing=False, version=2)
writer_queue = modal.Queue.from_name("som-writer-permit", create_if_missing=False)
image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install_from_requirements("service/requirements.txt")
)
deploy_mms_tts = os.environ.get("SOM_DEPLOY_MMS_TTS") == "1"
release_sha = os.environ.get("SOM_DEPLOY_SOURCE_SHA", "")
if release_sha:
    if not re.fullmatch(r"[a-f0-9]{40}", release_sha):
        raise ValueError("SOM_DEPLOY_SOURCE_SHA must be an exact commit")
    image = image.env({"SOM_RELEASE_SHA": release_sha})
mms_image = None
if deploy_mms_tts:
    # The writer's base image never receives Torch, model assets or inference.
    # All CPU model work belongs to an independent resource-free private class.
    models = os.environ.get("SOM_DEPLOY_MMS_TTS_DIR", "/private/tmp/cx1-som-tts-20261103/models")
    mms_image = (image.pip_install_from_requirements("service/requirements-tts-cpu.txt")
             .env({"SOM_MMS_TTS_EVALUATION": "1",
                   "SOM_MMS_TTS_DIR": "/opt/som-mms", "HF_HUB_OFFLINE": "1",
                   "TRANSFORMERS_OFFLINE": "1", "TOKENIZERS_PARALLELISM": "false",
                   "OMP_NUM_THREADS": "2", "MKL_NUM_THREADS": "2"})
             .add_local_dir(models, "/opt/som-mms", copy=True)
             .add_local_dir("service", "/app/service", copy=True)
             .add_local_file("scripts/verify_mms_runtime.py", "/app/scripts/verify_mms_runtime.py", copy=True)
             .run_commands("python /app/scripts/verify_mms_runtime.py --models /opt/som-mms --stress"))
    image = image.env({"SOM_REMOTE_MMS_TTS": "1"})
image = (image.add_local_dir("service", "/app/service")
         .add_local_dir("harness-bench", "/app/harness-bench")
         .add_local_dir("runtime", "/app/runtime"))


class MmsWorker:
    """Private CPU worker: no state Volume, writer permit or account secrets."""
    @modal.enter()
    def load(self):
        import sys
        sys.path.insert(0, "/app")
        from scripts.verify_mms_runtime import verify_runtime
        self.speech, _ = verify_runtime(os.environ["SOM_MMS_TTS_DIR"])

    @modal.method()
    def speak(self, text, language):
        from service.mms_tts import spoken_text
        from service.speech import validate_wav
        if spoken_text(text, language) != text:
            raise ValueError("canonical_speech_text_required")
        audio = self.speech.synthesize(text, language)
        validate_wav(audio)
        return audio


if deploy_mms_tts:
    MmsWorker = app.cls(image=mms_image, cpu=1, memory=3072,
                        min_containers=0, max_containers=1, buffer_containers=0,
                        scaledown_window=60, retries=0,
                        startup_timeout=180, timeout=120,
                        secrets=[], volumes={}, block_network=True,
                        restrict_modal_access=True)(MmsWorker)


class RemoteMmsSpeech:
    """Lightweight writer-side adapter; only canonical text and language cross RPC."""
    def __init__(self, worker):
        from service.mms_tts import speech_revision
        self.revision = speech_revision()
        self.worker = worker

    def synthesize(self, text, language):
        from service.mms_tts import spoken_text
        from service.speech import validate_wav
        # Keep unsupported normalization errors distinct and before any RPC.
        canonical = spoken_text(text, language)
        try:
            audio = self.worker.speak.remote(canonical, language)
            validate_wav(audio)
            return audio
        except Exception:
            # OOM, timeout and remote diagnostics never kill the writer process
            # or escape to the browser. Existing speech routes map this to 502.
            raise ValueError("speech_unavailable") from None


class WriterPermitApp:
    """ASGI wrapper returning the writer permit on lifespan shutdown.

    Wraps (and preserves) the inner app's lifespan: all lifespan
    messages are forwarded to the inner app. When the inner app
    reports ``lifespan.shutdown.complete``, the wrapper first runs
    ``volume.commit()`` and only then returns the permit via
    ``queue.put(permit)``, exactly once (repeated shutdowns do not
    duplicate the return). If the commit fails, the permit is never
    released and ``lifespan.shutdown.failed`` is sent instead of
    ``complete``. If the inner app reports startup/shutdown failure,
    the permit is not released (fail-closed).
    """

    def __init__(self, inner, volume, queue, permit):
        self.inner = inner
        self._volume = volume
        self._queue = queue
        self._permit = permit
        self._released = False

    def _release_once(self):
        if self._released:
            return
        # Commit first; only return the permit if commit succeeds.
        self._volume.commit()
        self._queue.put(self._permit)
        self._released = True

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "lifespan":
            await self.inner(scope, receive, send)
            return

        async def _send(message):
            if message.get("type") == "lifespan.shutdown.complete":
                try:
                    self._release_once()
                except Exception as exc:
                    await send({"type": "lifespan.shutdown.failed", "message": f"writer permit release failed: {exc}"})
                    return
            await send(message)

        await self.inner(scope, receive, _send)


def build_writer_app(queue, volume, app_factory):
    """Acquire permit -> reload -> build inner app -> wrap lifespan.

    Acquire happens BEFORE volume.reload() and before any DB init
    inside ``app_factory``. If the permit is unavailable, or if
    reload / factory startup fails after acquisition, this raises
    and fails closed: the permit is intentionally NOT returned
    (no commit/put), so a later start cannot become a second
    writer; operator reconciliation is required.
    """
    permit = queue.get(block=True, timeout=30)
    if permit is None:
        raise RuntimeError("writer permit unavailable; failing closed (operator reconciliation required)")
    volume.reload()
    # Factory may open SQLite / run on_write commits. Any failure
    # here propagates fail-closed with the permit still held.
    inner = app_factory()
    return WriterPermitApp(inner, volume, queue, permit)


@app.function(
    image=image, cpu=1, memory=512, min_containers=0, max_containers=1, buffer_containers=0,
    scaledown_window=60, volumes={"/data/som": volume},
    secrets=[
        modal.Secret.from_name("som-pilot"),  # existing model and private pilot credentials
        modal.Secret.from_name("som-participants"),  # participant password hashes, allowed preview Origin, heart signing key
    ],
)
@modal.asgi_app()
def web():
    import os, sys
    sys.path.insert(0, "/app")
    os.environ.setdefault("SERVICE_DATA_DIR", "/data/som")
    speech = None
    if os.environ.get("SOM_REMOTE_MMS_TTS") == "1":
        # A lazy handle in the explicit pilot namespace, never a public endpoint.
        worker = modal.Cls.from_name("souls-of-muse-harness", "MmsWorker",
                                     environment_name="souls-of-muse-pilot")()
        speech = RemoteMmsSpeech(worker)

    def _factory():
        from service.app import create_app
        return create_app(data_dir="/data/som", on_write=lambda: volume.commit(), speech=speech)

    return build_writer_app(writer_queue, volume, _factory)
# Volume commit runs after every state/budget mutation via on_write.
# Do not scale writers.
