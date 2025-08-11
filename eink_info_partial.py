#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import psutil
import datetime
import smbus
import time
from PIL import Image, ImageDraw, ImageFont
from epd_wrapper import EPDWrapper

# ========== настройки ==========
UPDATE_INTERVAL = 3          # сек между проверками данных
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_SIZE = 14
I2C_BUS = 1
UPS_I2C_ADDR = 0x43
ORIENTATION = "portrait"     # "portrait" или "landscape"
# =================================

def get_battery_percentage():
    try:
        bus = smbus.SMBus(I2C_BUS)
        read = bus.read_word_data(UPS_I2C_ADDR, 0x02)
        swapped = ((read << 8) & 0xFF00) + (read >> 8)
        percentage = swapped / 256
        return int(percentage)
    except Exception as e:
        # не критично — возвращаем None или 0
        print("[UPS error]", e)
        return None

def get_cpu_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            t = float(f.readline().strip()) / 1000.0
            return round(t, 1)
    except Exception as e:
        print("[CPU temp error]", e)
        return None

def draw_status(image, font, now, cpu, ram, swap, batt, temp):
    draw = ImageDraw.Draw(image)
    y = 2
    lh = FONT_SIZE + 4
    draw.text((4, y), now, font=font, fill=0); y += lh
    draw.text((4, y), f"CPU: {cpu}%", font=font, fill=0); y += lh
    draw.text((4, y), f"RAM: {ram}%", font=font, fill=0); y += lh
    draw.text((4, y), f"SWAP:{swap}%", font=font, fill=0); y += lh
    draw.text((4, y), f"BAT: {batt if batt is not None else 'N/A'}%", font=font, fill=0); y += lh
    draw.text((4, y), f"T: {temp if temp is not None else 'N/A'} C", font=font, fill=0)
    return image

def main():
    epd = EPDWrapper(orientation=ORIENTATION)
    epd.init_full()

    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)

    # prepare base image and write initial content (full update)
    base = epd.new_image()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    cpu = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory().percent
    swap = psutil.swap_memory().percent
    batt = get_battery_percentage()
    temp = get_cpu_temp()
    draw_status(base, font, now, cpu, ram, swap, batt, temp)

    # full base draw (this sets reference image)
    epd.set_base(base)

    # keep last_data for change detection
    last = {
        "cpu": cpu,
        "ram": ram,
        "swap": swap,
        "batt": batt,
        "temp": temp,
        "now": now
    }

    try:
        while True:
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            cpu = psutil.cpu_percent(interval=0.5)
            ram = psutil.virtual_memory().percent
            swap = psutil.swap_memory().percent
            batt = get_battery_percentage()
            temp = get_cpu_temp()

            cur = {"cpu": cpu, "ram": ram, "swap": swap, "batt": batt, "temp": temp, "now": now}

            # If something changed (except time), perform partial update.
            # you can be stricter: update only on CPU or battery change etc.
            changed = any(cur[k] != last.get(k) for k in ("cpu","ram","swap","batt","temp"))

            if changed:
                # draw only updated content onto a fresh image and send partial update
                img = epd.new_image()
                draw_status(img, font, now, cpu, ram, swap, batt, temp)
                epd.display_partial(img)
                # update last
                last.update(cur)

            time.sleep(UPDATE_INTERVAL)
    except KeyboardInterrupt:
        print("Exiting, sleeping epd")
        epd.clear(0xFF)
        epd.sleep()

if __name__ == "__main__":
    main()
