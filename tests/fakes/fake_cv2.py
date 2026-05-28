import numpy as np


class FakeCv2:
    """
    Drop-in replacement for the cv2 module used in analisar_visual().

    Pass key_sequence to control which keys the "operator" presses.
    Each call to waitKey() consumes the next key; when exhausted returns ord('q').
    """

    WINDOW_NORMAL = 0
    WINDOW_FULLSCREEN = 1
    WND_PROP_FULLSCREEN = 0
    FONT_HERSHEY_SIMPLEX = 0

    def __init__(self, key_sequence=None):
        self._keys = iter(key_sequence if key_sequence is not None else [ord("q")])
        self.shown_images = []

    def namedWindow(self, name, flags=None):
        pass

    def setWindowProperty(self, name, prop, value):
        pass

    def imread(self, path):
        return np.zeros((100, 100, 3), dtype=np.uint8)

    def rectangle(self, img, pt1, pt2, color, thickness):
        pass

    def addWeighted(self, src1, alpha, src2, beta, gamma, dst=None):
        return src1.copy()

    def putText(self, img, text, org, fontFace, fontScale, color, thickness):
        pass

    def imshow(self, name, img):
        self.shown_images.append(img.copy() if img is not None else None)

    def waitKey(self, delay):
        try:
            return next(self._keys)
        except StopIteration:
            return ord("q")

    def destroyAllWindows(self):
        pass
