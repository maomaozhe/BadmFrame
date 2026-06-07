import sys
from types import SimpleNamespace

import pytest

from app.utils import ffmpeg


@pytest.mark.anyio
async def test_extract_metadata_falls_back_to_opencv_when_ffprobe_is_missing(tmp_path, monkeypatch):
    video_path = tmp_path / "sample.mp4"
    video_path.write_bytes(b"video")

    async def fake_run_ffprobe(_file_path):
        raise FileNotFoundError("ffprobe")

    class FakeCapture:
        def __init__(self, path):
            self.path = path

        def isOpened(self):
            return True

        def get(self, prop):
            return {
                3: 1920,
                4: 1080,
                5: 29.0,
                7: 18891,
            }.get(prop, 0)

        def release(self):
            pass

    fake_cv2 = SimpleNamespace(
        CAP_PROP_FRAME_WIDTH=3,
        CAP_PROP_FRAME_HEIGHT=4,
        CAP_PROP_FPS=5,
        CAP_PROP_FRAME_COUNT=7,
        VideoCapture=FakeCapture,
    )

    monkeypatch.setattr(ffmpeg, "_run_ffprobe", fake_run_ffprobe)
    monkeypatch.setitem(sys.modules, "cv2", fake_cv2)

    meta = await ffmpeg.extract_metadata(video_path)

    assert meta.duration_sec == pytest.approx(651.413793, abs=0.001)
    assert meta.width == 1920
    assert meta.height == 1080
    assert meta.frame_rate == 29.0
    assert meta.codec == "unknown"
    assert meta.is_vfr is False
