class Adapter:
    """Единый интерфейс моделей для Harness. Реализации: MockAdapter, MetaAdapter."""
    name = "base"

    def complete(self, role, system, user, fault="none"):
        """Текстовый вызов роли (interpreter/reviewer/orchestrator).
        Возвращает {text, usage, latency_s}."""
        raise NotImplementedError

    def transcribe(self, wav_path, keywords=None, language_bias=None):
        """ASR файла. Возвращает {text, latency_s, seconds}."""
        raise NotImplementedError

    def segment(self, image_path, prompt):
        """Сегментация по текстовому промпту (маска лиц). Возвращает {masks, latency_s}."""
        raise NotImplementedError
