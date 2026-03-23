"""
Controller: Camera & Microphone live test.
Mở camera qua OpenCV, thu âm qua sounddevice, phân tích chất lượng.
Trả về CamMicTestResult qua callback.
"""
from __future__ import annotations

import base64
import io
import threading
from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class CamMicTestResult:
    # Camera
    camera_accessible: bool = False
    camera_frame_b64: Optional[str] = None   # base64 PNG để hiển thị
    camera_brightness: Optional[float] = None
    camera_sharpness: Optional[float] = None
    camera_quality: str = ""   # "good" | "poor" | "fail"
    camera_index: int = -1

    # Mic
    mic_accessible: bool = False
    mic_rms: Optional[float] = None
    mic_peak: Optional[float] = None
    mic_quality: str = ""   # "good" | "low" | "fail"

    # Speaker
    speaker_ok: bool = False
    speaker_quality: str = ""  # "ok" | "fail"

    error: str = ""

    @property
    def checklist_camera_idx(self) -> Optional[int]:
        """Trả về index option checklist phù hợp (0/1/2), None nếu chưa test."""
        if self.camera_quality == "good":
            return 0   # Hoạt động tốt
        if self.camera_quality == "poor":
            return 1   # Chất lượng kém
        if self.camera_quality == "fail":
            return 2   # Không hoạt động
        return None


class CamMicController:
    def __init__(self):
        self._on_start: Optional[Callable] = None
        self._on_result: Optional[Callable[[CamMicTestResult], None]] = None
        self._on_speaker_done: Optional[Callable[[bool], None]] = None
        self._on_speaker_start: Optional[Callable] = None
        self._running = False
        self._speaker_running = False

    def set_callbacks(
        self,
        on_start: Optional[Callable] = None,
        on_result: Optional[Callable[[CamMicTestResult], None]] = None,
        on_speaker_done: Optional[Callable[[bool], None]] = None,
        on_speaker_start: Optional[Callable] = None,
    ):
        self._on_start = on_start
        self._on_result = on_result
        self._on_speaker_done = on_speaker_done
        self._on_speaker_start = on_speaker_start

    def reset(self):
        self._running = False
        self._speaker_running = False

    def test(self):
        """Bắt đầu test camera + mic trong background thread."""
        if self._running:
            return
        self._running = True
        if self._on_start:
            self._on_start()
        threading.Thread(target=self._run, daemon=True).start()

    def test_speaker(self):
        """Phát tone loud→quiet→loud để test loa."""
        if self._speaker_running:
            return
        self._speaker_running = True
        # Báo UI biết đang phát
        if self._on_speaker_start:
            self._on_speaker_start()
        threading.Thread(target=self._run_speaker, daemon=True).start()

    # ── Private ───────────────────────────────────────────────────────────────

    def _run(self):
        result = CamMicTestResult()
        try:
            self._test_camera(result)
            self._test_mic(result)
        except Exception as e:
            result.error = str(e)
        finally:
            self._running = False
            if self._on_result:
                self._on_result(result)

    def _run_speaker(self):
        ok = False
        try:
            import numpy as np
            import sounddevice as sd
            RATE = 44100
            DURATION = 2.5
            FREQ = 440   # La4
            t = np.linspace(0, DURATION, int(RATE * DURATION), dtype=np.float32)
            # Envelope: to → nhỏ → to (hình chữ V lật ngược: 1→0→1)
            envelope = np.abs(2 * t / DURATION - 1).astype(np.float32)
            tone = (envelope * 0.75 * np.sin(2 * np.pi * FREQ * t)).astype(np.float32)
            sd.play(tone, RATE)
            sd.wait()
            ok = True
        except Exception:
            ok = False
        finally:
            self._speaker_running = False
            if self._on_speaker_done:
                self._on_speaker_done(ok)

    def _test_camera(self, result: CamMicTestResult):
        import os
        # macOS AVFoundation yêu cầu set env var khi gọi từ background thread
        os.environ.setdefault("OPENCV_AVFOUNDATION_SKIP_AUTH", "1")

        try:
            import cv2
            import numpy as np
        except ImportError:
            result.camera_quality = "fail"
            result.error = "Thiếu opencv-python"
            return

        cap = None
        for idx in range(4):
            c = cv2.VideoCapture(idx)
            if c.isOpened():
                cap = c
                result.camera_index = idx
                break
            c.release()

        if cap is None:
            result.camera_quality = "fail"
            import platform
            if platform.system() == "Darwin":
                result.error = "Chưa cấp quyền camera — vào System Settings > Privacy > Camera"
            return

        try:
            # Đọc vài frame để camera warm-up
            for _ in range(5):
                cap.read()

            ret, frame = cap.read()
            if not ret or frame is None:
                result.camera_quality = "fail"
                return

            result.camera_accessible = True

            # Phân tích chất lượng
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            brightness = float(np.mean(gray))
            sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())

            result.camera_brightness = round(brightness, 1)
            result.camera_sharpness = round(sharpness, 1)

            # Phân loại chất lượng
            if brightness < 20 or brightness > 235:
                result.camera_quality = "poor"   # quá tối / quá sáng
            elif sharpness < 50:
                result.camera_quality = "poor"   # mờ
            else:
                result.camera_quality = "good"

            # Encode frame thành base64 PNG (resize nhỏ để hiển thị)
            thumb_w = 240
            h, w = frame.shape[:2]
            if w == 0:
                return
            thumb_h = int(h * thumb_w / w)
            thumb = cv2.resize(frame, (thumb_w, thumb_h))
            rgb = cv2.cvtColor(thumb, cv2.COLOR_BGR2RGB)

            from PIL import Image as PILImage
            img = PILImage.fromarray(rgb)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=80)
            result.camera_frame_b64 = base64.b64encode(buf.getvalue()).decode()

        finally:
            cap.release()

    def _test_mic(self, result: CamMicTestResult):
        try:
            import sounddevice as sd
            import numpy as np
        except ImportError:
            result.mic_quality = "fail"
            return

        RATE = 16000
        DURATION = 1.5   # giây

        try:
            audio = sd.rec(
                int(RATE * DURATION),
                samplerate=RATE,
                channels=1,
                dtype="float32",
            )
            sd.wait()

            rms = float(np.sqrt(np.mean(audio ** 2)))
            peak = float(np.max(np.abs(audio)))

            result.mic_accessible = True
            result.mic_rms = round(rms, 6)
            result.mic_peak = round(peak, 4)

            if rms < 0.0003:
                result.mic_quality = "fail"   # không có tín hiệu
            elif rms < 0.005:
                result.mic_quality = "low"    # tín hiệu yếu
            else:
                result.mic_quality = "good"

        except Exception as e:
            result.mic_quality = "fail"
            result.error = (result.error + f" Mic: {e}").strip()
