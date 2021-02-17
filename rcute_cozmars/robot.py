"""
There are three different modes to connect and control the robot:

* :class:`Robot` executes each command sequentially in a blocking manner.

* :class:`AsyncRobot` executes commands in non-blocking manner, :class:`concurrent.futures.Future` objects are returned for time-consuming commands.

* :class:`AioRobot` works with asyncio, it executes commands asynchronously in async/await style.

.. |Latest version on pypi| raw:: html

    <a href='https://pypi.org/project/rcute-cozmars-server' target='blank'>The latest version on pypi</a>

.. warning::

    The robot accepts only one connection the same time. If Scratch is controlling Cozmars, the Python program will not be able to connect, and vice versa

"""
import sys
import asyncio
import aiohttp
import websockets
import threading
import json
import io
import functools
import wave
from wsmprpc import RPCClient, RPCStream
from . import util, env, screen, camera, microphone, button, sonar, infrared, lift, head, buzzer, speaker, motor, eye_animation
from .animation import animations
from .util import logger

class AioRobot:
    """Async/await mode of Cozmars robot

    :param serial_or_ip: IP address or serial number of Cozmars to connect. Default to None, in which case the program will automatically detect the robot on connection if there's only one found.
    :type serial_or_ip: str
    """
    def __init__(self, serial_or_ip=None):
        if serial_or_ip:
            self._host = 'rcute-cozmars-' + serial_or_ip + '.local' if len(serial_or_ip) == 4 else serial_or_ip
        self._mode = 'aio'
        self._connected = False
        self._env = env.Env(self)
        self._screen = screen.Screen(self)
        self._camera = camera.Camera(self)
        self._microphone = microphone.Microphone(self)
        self._button = button.Button(self)
        self._sonar = sonar.Sonar(self)
        self._infrared = infrared.Infrared(self)
        self._lift = lift.Lift(self)
        self._head = head.Head(self)
        self._buzzer = buzzer.Buzzer(self)
        self._speaker = speaker.Speaker(self)
        self._motor = motor.Motor(self)
        self._eye_anim = eye_animation.EyeAnimation(self)

    def _in_event_loop(self):
        return True

    @util.mode()
    async def animate(self, name, *args, **kwargs):
        """perform animation

        :param name: the name of the animation
        :type name: str
        """
        anim = animations[name]
        anim = getattr(anim, 'animate', anim)
        await anim(self, *args, **kwargs)

    @property
    def animation_list(self):
        """ """
        return list(animations.keys())

    @property
    def eyes(self):
        """eye animation on screen"""
        return self._eye_anim

    @property
    def env(self):
        """Environmental Variables"""
        return self._env

    @property
    def button(self):
        """ """
        return self._button

    @property
    def infrared(self):
        """Infrared sensor at the bottom of the robot"""
        return self._infrared

    @property
    def sonar(self):
        """Sonar, namely ultrasonic distance sensor"""
        return self._sonar

    @property
    def motor(self):
        """ """
        return self._motor

    @property
    def head(self):
        """ """
        return self._head

    @property
    def lift(self):
        """ """
        return self._lift

    @property
    def buzzer(self):
        """only for Cozmars V1"""
        if self.firmware_version.startswith('2'):
            raise AttributeError('Cozmars V2 has no buzzer')
        return self._buzzer

    @property
    def speaker(self):
        """only for Cozmars V2"""
        if self.firmware_version.startswith('1'):
            raise AttributeError('Cozmars V1 has no speaker')
        return self._speaker

    @property
    def screen(self):
        """ """
        return self._screen

    @property
    def camera(self):
        """ """
        return self._camera

    @property
    def microphone(self):
        """ """
        return self._microphone

    async def connect(self):
        """ """
        if not self._connected:
            if not hasattr(self, '_host'):
                found = await util.find_service('rcute-cozmars-????', '_ws._tcp.local.')
                assert len(found)==1, "More than one cozmars found." if found else "No cozmars found."
                self._host = found[0].server
            self._ws = await websockets.connect(f'ws://{self._host}/rpc')
            if '-1' == await self._ws.recv():
                raise RuntimeError('Could not connect to Cozmars, please close other programs that are already connected to Cozmars')
            self._rpc = RPCClient(self._ws)
            self._eye_anim_task = asyncio.create_task(self._eye_anim.animate(self))
            self._about = json.loads(await self._get('/about'))
            await self._env.load()
            self._sensor_task = asyncio.create_task(self._get_sensor_data())
            self._connected = True

    @property
    def connected(self):
        """ """
        return self._connected

    async def _call_callback(self, cb, *args):
        if cb:
            if self._mode == 'aio':
                (await cb(*args)) if asyncio.iscoroutinefunction(cb) else cb(*args)
            else:
                self._lo.run_in_executor(None, cb, *args)

    async def _get_sensor_data(self):
        self._sensor_data_rpc = self._rpc.sensor_data()
        async for event, data in self._sensor_data_rpc:
            try:
                if event == 'pressed':
                    if not data:
                        self.button._held = self.button._double_pressed = False
                    self.button._pressed = data
                    await self._call_callback(self.button.when_pressed if data else self.button.when_released)
                elif event == 'held':
                    self.button._held = data
                    await self._call_callback(self.button.when_held)
                elif event == 'double_pressed':
                    self.button._pressed = data
                    self.button._double_pressed = data
                    await self._call_callback(self.button.when_pressed)
                    await self._call_callback(self.button.when_double_pressed)
                elif event == 'out_of_range':
                    await self._call_callback(self.sonar.when_out_of_range, data)
                elif event == 'in_range':
                    await self._call_callback(self.sonar.when_in_range, data)
                elif event == 'lir':
                    self.infrared._state = data, self.infrared._state[1]
                    await self._call_callback(self.infrared.when_state_changed, self.infrared._state)
                elif event == 'rir':
                    self.infrared._state = self.infrared._state[0], data
                    await self._call_callback(self.infrared.when_state_changed, self.infrared._state)
            except Exception as e:
                logger.exception(e)

    async def disconnect(self):
        """ """
        if self._connected:
            await self.when_called(None)
            self._sensor_task.cancel()
            self._eye_anim_task.cancel()
            self._sensor_data_rpc.cancel()
            await asyncio.gather(self.camera.close(), self.microphone.close(), self.speaker.close(), return_exceptions=True)
            await self._ws.close()
            self._connected = False

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.disconnect()

    @util.mode(force_sync=False)
    async def forward(self, duration=None):
        """

        :param duration: duration (seconds), default is None for non-stop
        :type duration: float
        """
        await self._rpc.speed((1,1), duration)

    @util.mode(force_sync=False)
    async def backward(self, duration=None):
        """

        :param duration: duration (seconds), default is None for non-stop
        :type duration: float
        """
        await self._rpc.speed((-1,-1), duration)

    @util.mode(force_sync=False)
    async def turn_left(self, duration=None):
        """

        :param duration: duration (seconds), default is None for non-stop
        :type duration: float
        """
        await self._rpc.speed((-1,1), duration)

    @util.mode(force_sync=False)
    async def turn_right(self, duration=None):
        """

        :param duration: duration (seconds), default is None for non-stop
        :type duration: float
        """
        await self._rpc.speed((1,-1), duration)

    @util.mode()
    async def stop(self):
        """ """
        await self._rpc.speed((0, 0))

    @util.mode()
    async def say(self, txt, repeat=1, **options):
        """Text to speach for Cozmars V2.

        `rcute-ai <https://rcute-ai.readthedocs.io/>`_ must be installed to support this function.

        :param txt: text to be said
        :type txt: str
        :param repeat: playback times, default is 1
        :type repeat: int, optional
        :param options:
            * voice/lang
            * volume
            * pitch
            * speed
            * word_gap

            See `rcute_ai.tts <https://rcute-ai.readthedocs.io/zh_CN/latest/api/tts.html#rcute_ai.tts.TTS.tts_wav/>`_
        :type options: optional
        """
        if not hasattr(self, '_tts'):
            import rcute_ai as ai
            self._tts = ai.TTS()
        op = self.env.vars.get('say', {}).get(sys.platform, {}).copy()
        op.update(options)
        wav_data = await self._lo.run_in_executor(None, functools.partial(self._tts.tts_wav, txt, **op))
        with wave.open(io.BytesIO(wav_data)) as f:
            await self.speaker.play(f.readframes(f.getnframes()), repeat=repeat, volume=self.env.vars.get('say_vol'), sample_rate=f.getframerate(), dtype='int16')

    @util.mode(property_type='setter')
    async def when_called(self, *args):
        """Callback function, called when the wake word 'R-Cute' or Chinese '阿Q' is detected.

        When set, a thread will be running in background using the robot's microphone. If set to `None`, the background thread will stop.

        `rcute-ai <https://rcute-ai.readthedocs.io/>`_ must be installed to support this function.

        See `rcute_ai.WakeWordDetector <https://rcute-ai.readthedocs.io/zh_CN/latest/api/WakeWordDetector.html>`_"""
        if not args:
            return getattr(self, '_when_called', None)
        cb = self._when_called = args[0]
        if cb:
            def wwd_run():
                if not hasattr(self, '_wwd'):
                    import rcute_ai as ai
                    self._wwd = ai.WakeWordDetector()
                logger.info('Start wake word detection.')
                with self.microphone.get_buffer() as buf:
                    while self._when_called:
                        self._wwd.detect(buf) and cb()
                logger.info('Stop wake word detection.')
            self._wwd_thread = threading.Thread(target=wwd_run, daemon=True)
            self._wwd_thread.start()
        else:
            hasattr(self, '_wwd') and self._wwd.cancel()
            hasattr(self, '_wwd_thread') and self._wwd_thread.is_alive() and await self._lo.run_in_executor(None, self._wwd_thread.join)

    @util.mode()
    async def listen(self, **kw):
        """Speech recognition.

        :param lang: language, default to `'en'`
        :type lang: str
        :return: recognized string
        :rtype: str

        other paramters are the same as `rcute_ai.STT.stt <https://rcute-ai.readthedocs.io/zh_CN/latest/api/STT.html#rcute_ai.STT.stt>`_ 's keyword arguments.

        `rcute-ai <https://rcute-ai.readthedocs.io/>`_ must be installed to support this function.
        """
        if not hasattr(self, '_stts'):
            self._stts = {}
        lang = kw.pop('lang', 'en')
        def stt_run():
            if not self._stts.get(lang):
                import rcute_ai as ai
                self._stts[lang] = ai.STT(lang=lang)
            with self.microphone.get_buffer() as buf:
                return self._stts[lang].stt(buf, **kw)
        return await self._lo.run_in_executor(None, stt_run)

    @property
    def hostname(self):
        """Cozmars URL"""
        return self._about['hostname']

    @property
    def ip(self):
        """Cozmars' IP address"""
        return self._about['ip']

    @property
    def firmware_version(self):
        """Cozmars firmware version"""
        return self._about['version']

    @property
    def mac(self):
        """Cozmars MAC address"""
        return self._about['mac']


    @property
    def serial(self):
        """Cozmars serial number"""
        return self._about['serial']

    @util.mode()
    async def poweroff(self):
        """ """
        await AioRobot.disconnect(self)
        try:
            await self._get('/poweroff')
        except Exception as e:
            pass

    @util.mode()
    async def reboot(self):
        """ """
        await AioRobot.disconnect(self)
        try:
            await self._get('/reboot')
        except Exception as e:
            pass

    async def _get(self, sub_url):
        async with aiohttp.ClientSession() as session:
            async with session.get('http://' + self._host + sub_url) as resp:
                return await resp.text()

class Robot(AioRobot):
    """Cozmars robot synchronization mode

    :param serial_or_ip: IP address or serial number of Cozmars to connect. Default to None, in which case the program will automatically detect the robot on connection if there's only one found.
    :type serial_or_ip: str
    """
    def __init__(self, serial_or_ip=None):
        AioRobot.__init__(self, serial_or_ip)
        self._mode = 'sync'

    def _in_event_loop(self):
        return self._event_thread == threading.current_thread()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.disconnect()

    def connect(self):
        """ """
        self._lo = asyncio.new_event_loop()
        self._event_thread = threading.Thread(target=self._run_loop, args=(self._lo,), daemon=True)
        self._event_thread.start()
        asyncio.run_coroutine_threadsafe(AioRobot.connect(self), self._lo).result()

    def disconnect(self):
        """ """
        asyncio.run_coroutine_threadsafe(AioRobot.disconnect(self), self._lo).result()
        self._lo.call_soon_threadsafe(self._done_ev.set)
        self._event_thread.join(timeout=5)

    def _run_loop(self, loop):
        asyncio.set_event_loop(loop)
        self._done_ev = asyncio.Event()
        loop.run_until_complete(self._done_ev.wait())
        tasks = asyncio.all_tasks(loop)
        for t in tasks:
            t.cancel()
        loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
        asyncio.set_event_loop(None)

class AsyncRobot(Robot):
    """Asynchronous (concurrent.futures.Future) mode of the Cozmars robot

    :param serial_or_ip: IP address or serial number of Cozmars to connect. Default to None, in which case the program will automatically detect the robot on connection if there's only one found.
    :type serial_or_ip: str
    """
    def __init__(self, serial_or_ip=None):
        Robot.__init__(self, serial_or_ip)
        self._mode = 'async'
