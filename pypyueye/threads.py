# -*- coding: utf-8 -*-
#!/usr/env python3

# Copyright (C) 2017 Gaby Launay

# Author: Gaby Launay  <gaby.launay@tutanota.com>

# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

__author__ = "Gaby Launay"
__copyright__ = "Gaby Launay 2017"
__credits__ = ""
__license__ = "GPL3"
__version__ = ""
__email__ = "gaby.launay@tutanota.com"
__status__ = "Development"


from pyueye import ueye
from threading import Thread
from .utils import ImageData, ImageBuffer
import cv2


class GatherThread(Thread):
    def __init__(self, cam, copy=True):
        """
        Thread used for gather images.
        """
        super().__init__()
        self.timeout = 1000
        self.cam = cam
        self.cam.capture_video()
        self.running = True
        self.copy = copy

    def run(self):
        while self.running:
            img_buffer = ImageBuffer()
            ret = ueye.is_WaitForNextImage(self.cam.handle(),
                                           self.timeout,
                                           img_buffer.mem_ptr,
                                           img_buffer.mem_id)
            if ret == ueye.IS_SUCCESS:
                imdata = ImageData(self.cam.handle(), img_buffer)
                self._process(imdata)

    def process(self, image_data):
        pass

    def _process(self, image_data):
        self.process(image_data)
        #image_data.unlock()

    def stop(self):
        self.cam.stop_video()
        self.running = False


class FrameThread(GatherThread):
    def __init__(self, cam, views=None, copy=True):
        """
        Thread used for live display.
        """
        super().__init__(cam=cam, copy=copy)
        self.views = views

    def process(self, image_data):
        if self.views:
            if type(self.views) is not list:
                self.views = [self.views]
            for view in self.views:
                view.handle(image_data)


class UselessThread(GatherThread):
    def __init__(self, cam, views=None, copy=True):
        """
        Thread used for debugging only.
        """
        super().__init__(cam=cam, copy=copy)
        self.views = views

    def process(self, image_data):
        import numpy as np
        new_exp = np.random.rand()*20
        self.cam.set_exposure(new_exp)


class SaveThread(GatherThread):
    def __init__(self, cam, path, copy=True):
        """
        Thread used for saving images.
        """
        super().__init__(cam=cam, copy=copy)
        self.path = path

    def process(self, image_data):
        cv2.imwrite(self.path, image_data.as_1d_image())
        self.stop()


class RecordThread(GatherThread):
    def __init__(self, cam, path, use_memory=False, frps=24, nmb_frame=10, copy=True,
                 verbose=False):
        """
        Thread used to record videos.
        """
        super().__init__(cam=cam, copy=copy)
        self.nmb_frame = nmb_frame
        self.use_memory = use_memory
        self.verbose = verbose
        self.ind_frame = 0
        self.path = path
        self.frps = frps
        # Create videowriter instance if needed
        if not self.use_memory:
            self.vw = self.open_video_writer()
        self.in_memory_images = []

    def open_video_writer(self):
        aoi = self.cam.get_aoi()
        fourcc = cv2.VideoWriter_fourcc("M", "J", "P", "G")
        return cv2.VideoWriter(self.path,
                               fourcc=fourcc,
                               fps=self.frps,
                               frameSize=(aoi.width, aoi.height),
                               isColor=0)
    def process(self, imdata):
        if self.use_memory:
            self.in_memory_images.append(imdata.as_1d_image())
        else:
            self.vw.write(imdata.as_1d_image())
        self.ind_frame += 1
        if self.verbose:
            print(f"\r{self.ind_frame}/{self.nmb_frame} frames taken", end="")
        # stop
        if self.ind_frame >= self.nmb_frame:
            print('\n')
            self.stop()

    def stop(self):
        if self.use_memory:
            print("Saving images to drive...")
            self.vw = self.open_video_writer()
            for i, im in enumerate(self.in_memory_images):
                print(f"\r{i}/{self.nmb_frame} frames saved", end="")
                self.vw.write(im)
            print("\nDone")
        self.vw.release()
        super().stop()
