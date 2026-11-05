"""Выход ансамбля на встроенном GM-синтезаторе macOS. Голоса: 0 бас, 1 аккордовый подклад, 2 щипковая краска.
GM-номера: 33 fingered bass, 29 overdriven guitar (мягкий перегруз), 30 distortion guitar (жёсткий), 48 strings,
107 koto / 106 shamisen (ближайшее к домбре в банке Apple), 108 kalimba / 114 steel drums / 11 vibraphone (ближайшее к хангу).
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "keys"))
from gm_synth import GMSynth

DEFAULT_VOICES = {"bass": "ebass", "pad": "strat", "pluck": 107}   # сэмплы Logic: пальцевый бас, Strat с мягким перегрузом; кото из GM
VOICE_GAIN = {"bass": 0.9, "pad": 0.5, "pluck": 0.8}
VOICE_DRIVE = {"bass": 0.0, "pad": 30.0, "pluck": 0.0}        # перегруз только у гитары, 30 % — мягкий

class EnsemblePlayer:
    def __init__(self, voices: dict | None = None, volume: float = 0.8):
        v = dict(DEFAULT_VOICES); v.update(voices or {})
        self.names = ["bass", "pad", "pluck"]
        self.ch = {i: GMSynth(v[n], volume=volume * VOICE_GAIN[n], overdrive=VOICE_DRIVE[n]) for i, n in enumerate(self.names)}
        self.programs = v
        # задержка вывода (сек): выходной узел + один буфер рендера (note_on попадает в следующий цикл); на ML1 ≈ 1,25 мс + 512/48000 ≈ 12 мс.
        # Follower берёт её как упреждение выдачи долей (lead), чтобы бас звучал на доле, а не после.
        try:
            o = self.ch[0].engine.outputNode()
            self.latency = float(o.presentationLatency()) + float(o.AUAudioUnit().maximumFramesToRender()) / float(o.outputFormatForBus_(0).sampleRate())
        except Exception:
            self.latency = 0.012
    def note_on(self, ch: int, midi: int, vel: int = 90): self.ch[ch].note_on(midi, vel)
    def note_off(self, ch: int, midi: int): self.ch[ch].note_off(midi)
    def set_voice(self, name: str, program: int): self.ch[self.names.index(name)].program(program); self.programs[name] = program
