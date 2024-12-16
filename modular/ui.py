#  OBS Smart Replays is an OBS script that allows more flexible replay buffer management:
#  set the clip name depending on the current window, set the file name format, etc.
#  Copyright (C) 2024 qvvonk
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.

import tkinter as tk
from tkinter import font as f

import time
import sys


# This part of the script uses only when it is run as a main program, not imported by OBS.
#
# You can run this script to show notification:
# python smart_replays.py <Notification Title> <Notification Text> <Notification Color>
class ScrollingText:
    def __init__(self, canvas: tk.Canvas, text, visible_area_width, start_pos, font, speed=1):
        """
        Scrolling text widget.

        :param canvas: canvas.
        :param text: text.
        :param visible_area_width: width of the visible area of the text.
        :param start_pos: text's start position (most likely padding from left border).
        :param font: font.
        :param speed: scrolling speed.
        """

        self.canvas = canvas
        self.text = text
        self.area_width = visible_area_width
        self.start_pos = start_pos
        self.font = font
        self.speed = speed

        self.text_width = font.measure(text)
        self.text_height = font.metrics("ascent") + font.metrics("descent")
        self.text_id = self.canvas.create_text(0, round((self.canvas.winfo_height() - self.text_height) / 2),
                                               anchor='nw', text=self.text, font=self.font, fill="#ffffff")
        self.text_curr_pos = start_pos
        self.canvas.after(1000, self.update_scroll)  # type: ignore

    def update_scroll(self):
        if self.text_curr_pos + self.text_width > self.area_width:
            self.canvas.move(self.text_id, -self.speed, 0)
            self.text_curr_pos -= self.speed

            self.canvas.after(20, self.update_scroll)  # type: ignore


class NotificationWindow:
    def __init__(self, title: str, message: str, main_color: str = "#76B900"):
        self.title = title
        self.message = message
        self.back_bg = main_color
        self.main_bg = "#000000"

        self.root = tk.Tk()
        self.root.withdraw()
        self.window = tk.Toplevel()
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True, "-alpha", 0.99)
        self.scr_w, self.scr_h = self.window.winfo_screenwidth(), self.window.winfo_screenheight()
        self.wnd_w, self.wnd_h = round(self.scr_w / 6.4) * 2, round(self.scr_h / 12)
        self.main_frm_padding = round(self.wnd_w / 80)
        self.content_frm_padding_x, self.content_frm_padding_y = round(self.wnd_w / 80), round(self.wnd_h / 12)
        # window width is x2 bigger, cz half of the window is out of screen

        self.wnd_x = self.scr_w - round(self.wnd_w / 2)  # half of the window is out of screen.
        self.wnd_y = round(self.scr_h / 10)
        self.main_frm_x, self.main_frm_y = round(self.wnd_w / 2), 0
        self.main_frm_w, self.main_frm_h = round(self.wnd_w / 2) - self.main_frm_padding, self.wnd_h

        self.title_font_size = round(self.wnd_h / 5)
        self.text_font_size = round(self.wnd_h / 8)

        self.green_frame = tk.Frame(self.window, bg=self.back_bg, bd=0)
        self.green_frame.pack(fill=tk.BOTH, expand=True)

        self.main_frame = tk.Frame(self.window, bg=self.main_bg, bd=0, width=self.main_frm_w, height=self.main_frm_h)
        self.main_frame.pack_propagate(False)
        self.main_frame.place(x=self.main_frm_x, y=0)
        self.main_frame.lift()

        self.content_frame = tk.Frame(self.main_frame, bg=self.main_bg, bd=0)
        self.content_frame.pack(fill=tk.BOTH, anchor=tk.W, padx=self.content_frm_padding_x,
                                pady=self.content_frm_padding_y)

        self.title_label = tk.Label(self.content_frame, text=self.title,
                                    font=("Bahnschrift", self.title_font_size, "bold"), bg=self.main_bg, fg=self.back_bg)
        self.title_label.pack(anchor=tk.W)

        self.canvas = tk.Canvas(self.content_frame, bg=self.main_bg, highlightthickness=0)
        self.canvas.pack(expand=True)
        self.canvas.update()
        font = f.Font(family="Cascadia Mono", size=self.text_font_size)
        message = ScrollingText(self.canvas, message, self.main_frm_w, self.content_frm_padding_x * 2, font=font,
                                speed=3)

    def animate_window(self, current_x: int, target_x: int, speed: int = 5):
        speed = speed if current_x < target_x else -speed
        curr_x = current_x
        for x in range(current_x, target_x, speed):
            curr_x = x
            self.window.geometry(f"+{x}+{self.wnd_y}")
            self.window.update()

        if curr_x != target_x:
            self.window.geometry(f"+{target_x}+{self.wnd_y}")
            self.window.update()

    def animate_main_frame(self, current_x: int, target_x: int, speed: int = 5):
        speed = speed if current_x < target_x else -speed
        curr_x = current_x
        for x in range(current_x, target_x, speed):
            curr_x = x
            self.main_frame.place(x=x, y=self.main_frm_y)
            self.window.update()
            time.sleep(0.001)

        if curr_x != target_x:
            self.main_frame.place(x=target_x, y=self.main_frm_y)
            self.window.update()

    def show(self):
        self.window.geometry(f"{self.wnd_w}x{self.wnd_h}+{0}+{self.wnd_y}")
        self.animate_window(self.scr_w, self.wnd_x)
        time.sleep(0.1)
        self.animate_main_frame(self.main_frm_x, self.main_frm_padding)
        self.window.after(5000, self.close)  # type: ignore
        self.root.mainloop()

    def close(self):
        self.animate_main_frame(self.main_frm_padding, self.main_frm_x)
        time.sleep(0.1)
        self.animate_window(self.wnd_x, self.scr_w)
        self.window.destroy()
        self.root.destroy()


if __name__ == '__main__':
    t = sys.argv[1] if len(sys.argv) > 1 else "Test Title"
    m = sys.argv[2] if len(sys.argv) > 2 else "Test Message"
    color = sys.argv[3] if len(sys.argv) > 3 else "#76B900"
    NotificationWindow(t, m, color).show()
    sys.exit(0)
