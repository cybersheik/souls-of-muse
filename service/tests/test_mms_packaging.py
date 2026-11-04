"""Exercise the opt-in image graph and startup ordering without Modal/cloud access."""
import os
from pathlib import Path
import runpy
import socket
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
TEMP_PARENT = '/private/tmp' if Path('/private/tmp').is_dir() else None


class ImageGraph:
    def __init__(self):
        self.steps = []
        self.mounted = False

    def step(self, kind, args, kwargs):
        if self.mounted and kind in {'env', 'pip', 'run', 'copy'}:
            raise AssertionError('image build or environment operation after a runtime mount')
        result = ImageGraph()
        result.mounted = self.mounted or kind == 'mount'
        result.steps = self.steps + [(kind, args, kwargs)]
        return result

    def pip_install_from_requirements(self, *args, **kwargs): return self.step('pip', args, kwargs)
    def env(self, *args, **kwargs): return self.step('env', args, kwargs)
    def run_commands(self, *args, **kwargs): return self.step('run', args, kwargs)
    def add_local_dir(self, *args, **kwargs): return self.step('copy' if kwargs.get('copy') else 'mount', args, kwargs)
    def add_local_file(self, *args, **kwargs): return self.step('copy' if kwargs.get('copy') else 'mount', args, kwargs)


def definition(enabled, image=None):
    image = image if image is not None else ImageGraph()
    decorated = []
    class App:
        def __init__(self, name): self.name = name; self.classes = []
        def function(self, **kwargs):
            decorated.append(kwargs)
            return lambda function: function
        def cls(self, **kwargs):
            self.classes.append(kwargs)
            return lambda cls: cls
    inert = types.SimpleNamespace(from_name=lambda *args, **kwargs: object())
    fake = types.SimpleNamespace(App=App, Volume=inert, Queue=inert, Secret=inert,
                                 Image=types.SimpleNamespace(debian_slim=lambda **kwargs: image),
                                 asgi_app=lambda: lambda function: function,
                                 enter=lambda: lambda function: function,
                                 method=lambda: lambda function: function)
    directory = tempfile.mkdtemp(prefix='cx1-mms-package-', dir=TEMP_PARENT)
    env = {'SOM_DEPLOY_MMS_TTS': '1' if enabled else '0', 'SOM_DEPLOY_MMS_TTS_DIR': directory,
           'SOM_DEPLOY_SOURCE_SHA': 'a' * 40}
    with patch.dict(sys.modules, {'modal': fake}), patch.dict(os.environ, env):
        namespace = runpy.run_path(str(ROOT / 'service/modal_app.py'))
    return namespace, getattr(namespace['image'], 'steps', None), decorated[0], directory


class MmsPackaging(unittest.TestCase):
    def test_default_image_keeps_512_without_torch_or_mms_assets(self):
        namespace, steps, function, _ = definition(False)
        self.assertEqual(function['memory'], 512)
        self.assertFalse(any('tts-cpu' in str(args) for kind, args, kwargs in steps))
        self.assertFalse(any(kind == 'run' for kind, args, kwargs in steps))
        self.assertEqual(namespace['app'].classes, [])

    def test_opt_in_image_copies_models_sets_offline_env_then_runs_preflight_before_mounts(self):
        namespace, web_steps, function, directory = definition(True)
        self.assertEqual(function['memory'], 512, 'writer must never share the TTS memory allocation')
        self.assertFalse(any('tts-cpu' in str(args) for kind, args, kwargs in web_steps))
        self.assertEqual(len(namespace['app'].classes), 1)
        worker = namespace['app'].classes[0]
        self.assertEqual(worker['memory'], 3072)
        self.assertEqual(worker['max_containers'], 1)
        self.assertEqual(worker.get('secrets'), [])
        self.assertEqual(worker.get('volumes'), {})
        self.assertNotIn('queue', worker)
        self.assertEqual(worker.get('retries'), 0)
        self.assertIsNone(worker.get('max_inputs'), 'do not recycle the loaded worker after every utterance')
        steps = worker['image'].steps
        self.assertTrue(any(kind == 'pip' and args == ('service/requirements-tts-cpu.txt',) for kind, args, kwargs in steps))
        base_install = next(index for index, (kind, args, kwargs) in enumerate(steps)
                            if kind == 'pip' and args == ('service/requirements.txt',))
        cpu_install = next(index for index, (kind, args, kwargs) in enumerate(steps)
                           if kind == 'pip' and args == ('service/requirements-tts-cpu.txt',))
        self.assertLess(base_install, cpu_install, 'standalone CPU overlay requires the base runtime installed first')
        self.assertTrue(any(kind == 'copy' and args[0] == directory for kind, args, kwargs in steps))
        environment = {}
        for kind, args, kwargs in steps:
            if kind == 'env': environment.update(args[0])
        self.assertEqual(environment['HF_HUB_OFFLINE'], '1')
        self.assertEqual(environment['TRANSFORMERS_OFFLINE'], '1')
        self.assertEqual(environment['SOM_MMS_TTS_EVALUATION'], '1')
        preflight = [index for index, (kind, args, kwargs) in enumerate(steps) if kind == 'run' and 'verify_mms_runtime.py' in str(args)]
        self.assertEqual(len(preflight), 1)
        self.assertIn('--stress', str(steps[preflight[0]][1]))
        mounts = [index for index, (kind, args, kwargs) in enumerate(steps) if kind == 'mount']
        self.assertTrue(not mounts or preflight[0] < min(mounts))

    def test_failed_worker_enter_has_no_writer_permit_or_volume_to_strand(self):
        namespace, _, _, _ = definition(True)
        worker = namespace['MmsWorker']()
        self.assertTrue('MmsWorker' in namespace, 'isolated MMS worker is required')
        def failure(*args, **kwargs):
            self.assertEqual(sys.path[0], '/app', 'worker must establish its own copied source path')
            raise RuntimeError('fixture invalid MMS dependency or assets')
        modules = {'scripts.verify_mms_runtime': types.SimpleNamespace(verify_runtime=failure)}
        with patch.dict(sys.modules, modules), patch.object(sys, 'path', sys.path.copy()), patch.dict(os.environ, {'SOM_MMS_TTS_DIR': '/fixture-only'}):
            with self.assertRaises(RuntimeError): worker.load()
        self.assertFalse(hasattr(worker, 'queue'))
        self.assertFalse(hasattr(worker, 'volume'))

    def test_cpu_requirements_pin_local_build_and_ci_exercises_real_wav(self):
        requirements = ROOT / 'service/requirements-tts-cpu.txt'
        self.assertTrue(requirements.is_file(), 'CPU-only pinned runtime is required')
        text = requirements.read_text()
        self.assertIn('torch==2.9.0+cpu', text)
        self.assertIn('https://download.pytorch.org/whl/cpu', text)
        self.assertIn('transformers==4.57.1', text)
        self.assertIn('numpy==2.2.6', text)
        workflow = (ROOT / '.github/workflows/offline-checks.yml').read_text()
        self.assertIn('service/requirements-tts-cpu.txt', workflow)
        self.assertIn('scripts/verify_mms_runtime.py', workflow)

    def test_cpu_manifest_survives_modals_single_file_requirements_copy(self):
        directory = Path(tempfile.mkdtemp(prefix='cx1-mms-requirements-', dir=TEMP_PARENT))
        staged = directory / '.requirements.txt'
        staged.write_text((ROOT / 'service/requirements-tts-cpu.txt').read_text())
        for line in staged.read_text().splitlines():
            if line.strip().startswith('-r '):
                relative = line.strip()[3:].strip()
                self.assertTrue((staged.parent / relative).is_file(),
                                'Modal copies only this manifest; nested relative requirements cannot resolve')

    def test_linux_wav_ci_is_valid_yaml_and_has_separate_asset_preparation(self):
        import yaml
        try:
            workflow = yaml.safe_load((ROOT / '.github/workflows/offline-checks.yml').read_text())
        except yaml.YAMLError:
            self.fail('Linux real-WAV job must be valid workflow YAML')
        self.assertIn('mms-cpu-runtime', workflow['jobs'])
        job = workflow['jobs']['mms-cpu-runtime']
        self.assertEqual(job['runs-on'], 'ubuntu-latest')
        runs = [step['run'] for step in job['steps'] if 'run' in step]
        install = next(run for run in runs if 'pip install' in run)
        self.assertIn('-r service/requirements.txt', install, 'clean Linux CI needs the base runtime as well as the CPU overlay')
        prepare = next(index for index, run in enumerate(runs) if 'service.prepare_mms' in run)
        verify = next(index for index, run in enumerate(runs) if 'scripts/verify_mms_runtime.py' in run)
        self.assertLess(prepare, verify)
        self.assertIn('--stress', runs[verify])

    def test_opt_in_definition_constructs_with_real_modal_image_sdk_without_network(self):
        import modal
        image = modal.Image.debian_slim(python_version='3.12')
        def forbidden(*args, **kwargs): raise AssertionError('dry image graph must not contact cloud')
        with patch.object(socket.socket, 'connect', forbidden), patch.object(socket, 'create_connection', forbidden):
            namespace, _, function, _ = definition(True, image=image)
        self.assertEqual(function['memory'], 512)
        self.assertIs(function['image'], namespace['image'])
        self.assertEqual(namespace['app'].classes[0]['memory'], 3072)

    def test_linux_preflight_refuses_nonlinux_and_wrong_cpu_build_before_inference(self):
        from scripts.verify_mms_runtime import verify_runtime
        with patch('platform.system', return_value='Darwin'), patch.dict(sys.modules, {'torch': None}):
            with self.assertRaises(RuntimeError): verify_runtime('/nonexistent-fixture')
        packages = {'torch': types.SimpleNamespace(__version__='2.9.0'),
                    'transformers': types.SimpleNamespace(__version__='4.57.1'),
                    'numpy': types.SimpleNamespace(__version__='2.2.6')}
        with patch('platform.system', return_value='Linux'), patch.dict(sys.modules, packages):
            with self.assertRaises(RuntimeError): verify_runtime('/nonexistent-fixture')

    def test_missing_manifest_asset_refuses_preflight_before_any_model_loading(self):
        from scripts.verify_mms_runtime import verify_runtime
        directory = tempfile.mkdtemp(prefix='cx1-mms-invalid-assets-', dir=TEMP_PARENT)
        torch = types.SimpleNamespace(__version__='2.9.0+cpu', version=types.SimpleNamespace(cuda=None),
            cuda=types.SimpleNamespace(is_available=lambda: False), set_num_threads=lambda value: None,
            get_num_interop_threads=lambda: 1)
        packages = {'torch': torch, 'transformers': types.SimpleNamespace(__version__='4.57.1'),
                    'numpy': types.SimpleNamespace(__version__='2.2.6')}
        with patch('platform.system', return_value='Linux'), patch.dict(sys.modules, packages):
            with self.assertRaises(ValueError): verify_runtime(directory)

    def _runtime_web(self):
        namespace, _, _, directory = definition(True)
        web = namespace['web']
        events = []
        queue = types.SimpleNamespace(get=lambda **kwargs: events.append('get') or 'original')
        volume = types.SimpleNamespace(reload=lambda: events.append('reload'), commit=lambda: None)
        remote = types.SimpleNamespace(speak=types.SimpleNamespace(remote=lambda text, lang: b'not-called-at-startup'))
        def factory(**kwargs):
            events.append('factory')
            self.assertIsInstance(kwargs['speech'], namespace['RemoteMmsSpeech'])
            return object()
        modules = {'service.app': types.SimpleNamespace(create_app=factory)}
        bindings = []
        def bind(*args, **kwargs):
            bindings.append((args, kwargs))
            return lambda: remote
        namespace['modal'].Cls = types.SimpleNamespace(from_name=bind)
        with patch.dict(web.__globals__, {'writer_queue': queue, 'volume': volume}), \
             patch.dict(sys.modules, modules), patch.object(sys, 'path', sys.path.copy()), \
             patch.dict(os.environ, {'SOM_REMOTE_MMS_TTS': '1'}):
            web()
        self.assertEqual(bindings, [(('souls-of-muse-harness', 'MmsWorker'), {'environment_name': 'souls-of-muse-pilot'})])
        return events

    def test_web_injects_only_remote_bridge_without_local_model_warmup(self):
        self.assertEqual(self._runtime_web(), ['get', 'reload', 'factory'])

    def test_worker_oom_is_a_sanitized_provider_failure_not_a_writer_failure(self):
        namespace, _, _, _ = definition(True)
        self.assertIn('RemoteMmsSpeech', namespace)
        def oom(*args): raise MemoryError('fixture worker OOM')
        worker = types.SimpleNamespace(speak=types.SimpleNamespace(remote=oom))
        bridge = namespace['RemoteMmsSpeech'](worker)
        from service.mms_tts import speech_revision
        self.assertEqual(bridge.revision, speech_revision())
        with self.assertRaises(ValueError) as error: bridge.synthesize('Play four beats.', 'en')
        self.assertNotIn('OOM', str(error.exception))

    def test_worker_reuses_a_single_loaded_provider_for_multiple_utterances(self):
        namespace, _, _, _ = definition(True)
        self.assertTrue('MmsWorker' in namespace, 'isolated MMS worker is required')
        worker = namespace['MmsWorker']()
        calls = []
        import io, wave
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as stream:
            stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(16000)
            stream.writeframes(b'\x01\x00' * 1600)
        audio = buffer.getvalue()
        speech = types.SimpleNamespace(synthesize=lambda text, lang: calls.append(('speak', text, lang)) or audio)
        def verify(models): calls.append(('load', models)); return speech, {}
        modules = {'scripts.verify_mms_runtime': types.SimpleNamespace(verify_runtime=verify)}
        with patch.dict(sys.modules, modules), patch.object(sys, 'path', sys.path.copy()), patch.dict(os.environ, {'SOM_MMS_TTS_DIR': '/fixture-only'}):
            worker.load()
            self.assertEqual(worker.speak('play four beats', 'en'), audio)
            self.assertEqual(worker.speak('hãy chơi bốn phách', 'vi'), audio)
        self.assertEqual([call[0] for call in calls], ['load', 'speak', 'speak'])
        self.assertIs(worker.speech, speech)

    def test_bridge_preserves_normalization_refusal_before_any_rpc(self):
        namespace, _, _, _ = definition(True)
        self.assertTrue('RemoteMmsSpeech' in namespace, 'remote bridge is required')
        calls = []
        worker = types.SimpleNamespace(speak=types.SimpleNamespace(remote=lambda *args: calls.append(args)))
        bridge = namespace['RemoteMmsSpeech'](worker)
        with self.assertRaises(ValueError) as error: bridge.synthesize('word ' * 60, 'en')
        self.assertNotEqual(str(error.exception), 'speech_unavailable')
        self.assertEqual(calls, [])

    def test_build_stress_cases_reach_the_normalized_limit_in_both_languages(self):
        from scripts import verify_mms_runtime as runtime
        self.assertTrue(hasattr(runtime, 'input_cases'), 'build and CI need explicit stress cases')
        short = runtime.input_cases(stress=False)
        self.assertEqual(len(short), 2)
        cases = runtime.input_cases(stress=True)
        stress = [(name, lang, text) for name, lang, text in cases if name.endswith('-stress')]
        self.assertEqual({lang for name, lang, text in stress}, {'en', 'vi'})
        from service.mms_tts import spoken_text
        for name, lang, text in stress:
            normalized = spoken_text(text, lang)
            self.assertGreaterEqual(len(normalized), 230)
            self.assertLessEqual(len(normalized), 240)
        self.assertIn(('vi-dense-stress', 'vi', 'la ' * 79 + 'sol'), cases)

    def test_memory_guard_reserves_application_headroom(self):
        from scripts import verify_mms_runtime as runtime
        self.assertTrue(hasattr(runtime, 'memory_usage'), 'preflight must enforce reserved app headroom')
        with patch.object(runtime.resource, 'getrusage', return_value=types.SimpleNamespace(ru_maxrss=3000 * 1024)):
            with self.assertRaises(RuntimeError): runtime.memory_usage()


if __name__ == '__main__': unittest.main()
