from . import util
from PIL import Image
import numpy as np

class Screen(util.Component):
    """显示屏"""

    def __init__(self, robot):
        util.Component.__init__(self, robot)
        self.default_fade_speed = None

    @property
    def resolution(self):
        """分辨率，`(240, 135)`，只读"""
        return 240, 135

    @property
    def max_brightness(self):
        """最大亮度， `1.0` ，只读"""
        return 1.0

    @property
    def min_brightness(self):
        """最低亮度， `0.0` ，黑屏，只读"""
        return .0

    @util.mode(property_type='setter')
    async def brightness(self, *args):
        """显示屏亮度，0~1，默认是 `0.1`
        """
        return await self._rpc.backlight(*args)

    @util.mode(force_sync=False)
    async def set_brightness(self, brightness, *, fade_duration=None, fade_speed=None):
        """设置显示屏亮度

        :param brightness: 亮度，0~1
        :type brightness: float
        :param fade_duration: 渐变时间（秒） ， 默认是 `None`，表示没有渐变
        :type fade_duration: float
        :param fade_speed: 渐变速度（/秒） ， 默认是 `None`，表示没有渐变
        :type fade_speed: float
        :raises TypeError: 不能同时设置 `fade_duration` 和 `fade_speed` ，否则抛出异常
        """
        if fade_duration and fade_speed:
            raise TypeError('Cannot set both fade_duration and fade_speed')
        await self._rpc.backlight(brightness, duration, fade_speed or self.default_fade_speed)

    @util.mode()
    async def fill(self, bgr, x=0, y=0, w=240, h=135):
        if not self._in_range((x, y), (w, h)):
            raise ValueError(f'Fill area must not exceed dimensions of screen {self.resolution}')
        x, y = y, 240-x-w
        await self._rpc.fill(bgr_to_color565(bgr), x, y, h, w)

    @util.mode()
    async def set_pixel(self, x, y, bgr):
        if not self._in_range((x, y)):
            raise ValueError(f'Pixel must not exceed dimensions of screen {self.resolution}')
        x, y = y, 240-x-1
        await self._rpc.pixel(x, y, bgr_to_color565(bgr))

    @util.mode()
    async def display(self, image, x=0, y=0):
        # if isinstance(image, Image):
        #     image = np.array(image.convert("RGB"))
        h, w, ch = image.shape
        if not self._in_range((x, y), (x+w, y+h)):
            raise ValueError(f'Image must not exceed dimensions of screen {self.resolution}')
        image = np.rot90(image)
        x, y = y, 240-x-w
        await self._rpc.display(image_to_data(image.astype('uint16')), x, y, x+h-1, y+w-1)

    @util.mode(force_sync=False)
    async def animate(self, gif, loop='auto'):
        await self._rpc.gif(gif, loop)

    def _in_range(self, *points):
        w, h = self.resolution
        for p in points:
            if 0>p[0]>w or 0>p[1]>h:
                return False
        return True


def bgr_to_color565(b, g=0, r=0):
    try:
        b, g, r = b
    except TypeError:
        pass
    return (r & 0xF8) << 8 | (g & 0xFC) << 3 | b >> 3

def image_to_data(bgr_image):
    # data = numpy.array(image.convert("RGB")).astype("uint16")
    color = (
    ((bgr_image[:, :, 2] & 0xF8) << 8)
    | ((bgr_image[:, :, 1] & 0xFC) << 3)
    | (bgr_image[:, :, 0] >> 3)
    )
    return np.dstack(((color >> 8) & 0xFF, color & 0xFF)).flatten().tolist()