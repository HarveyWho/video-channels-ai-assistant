"""Local-only screen capture and OCR. Screen images never go to the API."""


def group_lines(rows):
    """Join fragments sharing a baseline, then conservatively join indented wraps."""
    parts = []
    for box, text, score in rows:
        if float(score) < 0.75 or not text.strip():
            continue
        xs, ys = [p[0] for p in box], [p[1] for p in box]
        parts.append((min(ys), min(xs), max(ys), max(xs), text.strip()))
    parts.sort()
    lines = []
    for top, left, bottom, right, text in parts:
        if lines:
            prev = lines[-1]
            h = max(1, min(bottom-top, prev[2]-prev[0]))
            if abs((top+bottom-prev[0]-prev[2])/2) < h*0.55 and 0 <= left-prev[3] < h*3:
                prev[4] += " " + text
                prev[3] = right
                continue
        lines.append([top, left, bottom, right, text])
    result = []
    previous = None
    for row in lines:
        text = row[4]
        if previous and result and (":" in result[-1] or "：" in result[-1]):
            gap = row[0]-previous[2]
            h = max(1, previous[2]-previous[0])
            if (0 <= gap < h*1.1 and row[1] > previous[1]+h and
                    ":" not in text and "：" not in text and
                    not result[-1].endswith(("?", "？", "。", "!", "！"))):
                result[-1] += text
                previous = row
                continue
        result.append(text)
        previous = row
    return result


def valid_region(region):
    if not isinstance(region, dict) or set(region) != {"left", "top", "width", "height"}:
        return False
    if not all(isinstance(v, int) and not isinstance(v, bool) for v in region.values()):
        return False
    return (40 <= region["width"] <= 10000 and 30 <= region["height"] <= 10000
            and abs(region["left"]) <= 50000 and abs(region["top"]) <= 50000)


def overlaps(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


class ScreenReader:
    def __init__(self):
        from rapidocr import RapidOCR
        self.engine = RapidOCR(params={
            "Global.log_level": "error", "Global.text_score": 0.75,
            "EngineConfig.onnxruntime.intra_op_num_threads": 2,
            "EngineConfig.onnxruntime.inter_op_num_threads": 1,
        })

    def read(self, capture, region):
        import numpy as np
        if not valid_region(region):
            raise ValueError("请重新选择弹幕区域。")
        screen = capture.monitors[0]
        if (region["left"] < screen["left"] or region["top"] < screen["top"] or
                region["left"]+region["width"] > screen["left"]+screen["width"] or
                region["top"]+region["height"] > screen["top"]+screen["height"]):
            raise ValueError("屏幕布局已变化，请重新选择弹幕区域。")
        image = np.array(capture.grab(region))[:, :, :3].copy()
        result = self.engine(image)
        if result.txts is None or result.boxes is None:
            return []
        return group_lines(zip(result.boxes, result.txts, result.scores))
