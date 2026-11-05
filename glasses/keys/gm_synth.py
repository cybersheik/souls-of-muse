"""Встроенный General-MIDI синтезатор macOS через AVAudioUnitSampler: без загрузок и внешних банков.
Банк: /System/Library/Components/CoreAudio.component/Contents/Resources/gs_instruments.dls (Apple GS/GM).
    s = GMSynth(program=65)   # 65 = Alto Sax, 0 = Acoustic Grand, 24 = Nylon Guitar, 40 = Violin, 56 = Trumpet, 73 = Flute
    s.note_on(60, 100); s.note_off(60); s.program(56)
"""
from __future__ import annotations
import threading, time, ctypes, ctypes.util, struct
import numpy as np
import AVFoundation as AV, Foundation as F
import warnings, objc
warnings.filterwarnings("ignore", category=objc.ObjCPointerWarning)   # audioUnit() отдаёт сырой указатель — это ожидаемо

def _coreaudio_output_devices() -> list[tuple[int, str]]:
    """[(AudioDeviceID, имя)] устройств с выходными потоками — через CoreAudio, чтобы направить AVAudioEngine не в системный выход."""
    ca = ctypes.cdll.LoadLibrary(ctypes.util.find_library("CoreAudio"))
    class AOPA(ctypes.Structure): _fields_ = [("sel", ctypes.c_uint32), ("scope", ctypes.c_uint32), ("el", ctypes.c_uint32)]
    cc = lambda t: struct.unpack(">I", t.encode())[0]
    addr = AOPA(cc("dev#"), cc("glob"), 0); size = ctypes.c_uint32()
    ca.AudioObjectGetPropertyDataSize(1, ctypes.byref(addr), 0, None, ctypes.byref(size))
    ids = (ctypes.c_uint32 * (size.value // 4))(); ca.AudioObjectGetPropertyData(1, ctypes.byref(addr), 0, None, ctypes.byref(size), ids)
    out = []
    import objc
    for d in ids:
        a = AOPA(cc("stm#"), cc("outp"), 0); n = ctypes.c_uint32()
        if ca.AudioObjectGetPropertyDataSize(d, ctypes.byref(a), 0, None, ctypes.byref(n)) or n.value == 0: continue
        a = AOPA(cc("lnam"), cc("glob"), 0); sz = ctypes.c_uint32(8); buf = ctypes.c_void_p()
        if ca.AudioObjectGetPropertyData(d, ctypes.byref(a), 0, None, ctypes.byref(sz), ctypes.byref(buf)): continue
        out.append((int(d), str(objc.objc_object(c_void_p=buf.value))))
    return out

DLS = "/System/Library/Components/CoreAudio.component/Contents/Resources/gs_instruments.dls"
GM_NAMES = {0: "piano", 4: "epiano", 11: "vibes", 19: "organ", 24: "guitar", 32: "bass", 40: "violin", 42: "cello",
            48: "strings", 56: "trumpet", 57: "trombone", 64: "soprano sax", 65: "alto sax", 66: "tenor sax",
            71: "clarinet", 73: "flute", 80: "lead", 88: "pad"}

EXS_DIR = "/Library/Application Support/Logic/Sampler Instruments/"
EXS = {  # сэмплированные инструменты из библиотеки Logic/GarageBand (что реально установлено на ML1)
    "strat": EXS_DIR + "08 Guitars/Vintage Strat.exs",
    "ebass": EXS_DIR + "02 Bass/02 Electric Bass/Fingerstyle Electric Bass.exs",
    "upright": EXS_DIR + "02 Bass/01 Acoustic Bass/Upright Jazz Bass.exs",
}

class GMSynth:
    """program: номер GM (0..127) или имя из EXS (сэмплированный инструмент Logic). overdrive: 0..100 — мягкий перегруз."""
    def __init__(self, program: int | str = 65, volume: float = 1.0, monitor: bool = False, overdrive: float = 0.0, device: str | None = None):
        self.engine = AV.AVAudioEngine.alloc().init()
        self.device = None
        if device:                                            # подстрока имени устройства вывода; иначе — системный выход по умолчанию (может быть Bluetooth!)
            cands = [(i, n) for i, n in _coreaudio_output_devices() if device.lower() in n.lower()]
            if not cands:
                print(f"GM: аудиоустройство «{device}» не найдено: " + ", ".join(n for _, n in _coreaudio_output_devices()) + " — играю в системный выход", flush=True)
                cands = []
        if device and cands:
            at = ctypes.cdll.LoadLibrary(ctypes.util.find_library("AudioToolbox")); at.AudioUnitSetProperty.restype = ctypes.c_int32
            au = self.engine.outputNode().audioUnit(); dev = ctypes.c_uint32(cands[0][0])
            r = at.AudioUnitSetProperty(ctypes.c_void_p(au.pointerAsInteger), 2000, 0, 0, ctypes.byref(dev), 4)   # kAudioOutputUnitProperty_CurrentDevice
            if r: raise RuntimeError(f"GM: не удалось назначить устройство «{cands[0][1]}» (OSStatus {r})")
            self.device = cands[0][1]; print(f"GM → «{self.device}»", flush=True)
        self.sampler = AV.AVAudioUnitSampler.alloc().init()
        self.engine.attachNode_(self.sampler)
        last = self.sampler
        if overdrive > 0:
            self.dist = AV.AVAudioUnitDistortion.alloc().init(); self.engine.attachNode_(self.dist)
            self.dist.loadFactoryPreset_(AV.AVAudioUnitDistortionPresetMultiDistortedFunk)
            self.dist.setWetDryMix_(float(overdrive)); self.dist.setPreGain_(-6.0)
            self.engine.connect_to_format_(self.sampler, self.dist, None); last = self.dist
        self.engine.connect_to_format_(last, self.engine.mainMixerNode(), None)
        self.engine.mainMixerNode().setOutputVolume_(volume)
        try: self.sampler.setMasterGain_(12.0)   # +9 дБ: динамики MacBook, слышно из-за пианино
        except Exception as e: print('masterGain:', e)
        self.rms = 0.0
        if monitor:
            def tap(buf, when):
                ch = buf.floatChannelData()
                if ch is None: return
                n = int(buf.frameLength())
                a = np.array(ch[0].as_tuple(n), dtype=np.float32)
                self.rms = float(np.sqrt((a * a).mean()))
            self.engine.mainMixerNode().installTapOnBus_bufferSize_format_block_(0, 1024, None, tap)
        ok, err = self.engine.startAndReturnError_(None)
        if not ok: raise RuntimeError(f"AVAudioEngine: {err}")
        self.program(program)
    def program(self, program: int | str):
        if isinstance(program, str) and not program.isdigit():
            path = EXS.get(program, program)
            ok, err = self.sampler.loadInstrumentAtURL_error_(F.NSURL.fileURLWithPath_(path), None)
            if not ok: raise RuntimeError(f"EXS {path}: {err}")
            self.current = program; return program
        url = F.NSURL.fileURLWithPath_(DLS)
        ok, err = self.sampler.loadSoundBankInstrumentAtURL_program_bankMSB_bankLSB_error_(url, int(program), 0x79, 0, None)
        if not ok: raise RuntimeError(f"loadSoundBank: {err}")
        self.current = int(program)
        return GM_NAMES.get(int(program), str(program))
    def note_on(self, midi: int, vel: int = 100):
        if not self.engine.isRunning():                       # движок останавливается при смене устройства/конфигурации — поднимаем молча
            ok, err = self.engine.startAndReturnError_(None)
            if not ok: print("GM: AVAudioEngine не перезапустился:", err, flush=True)
        self.sampler.startNote_withVelocity_onChannel_(int(midi), int(vel), 0)
    def note_off(self, midi: int): self.sampler.stopNote_onChannel_(int(midi), 0)

if __name__ == "__main__":
    import sys
    prog = int(sys.argv[1]) if len(sys.argv) > 1 else 65
    s = GMSynth(prog, monitor=True); print("instrument:", GM_NAMES.get(prog, prog))
    peak = 0.0
    for m in (60, 64, 67, 72):
        s.note_on(m, 100)
        for _ in range(6): time.sleep(0.05); peak = max(peak, s.rms)
        s.note_off(m); time.sleep(0.1)
    time.sleep(0.5); print("peak rms while playing:", round(peak, 4))
