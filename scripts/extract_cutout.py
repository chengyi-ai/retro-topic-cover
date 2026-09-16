#!/usr/bin/env python3
"""Traditional GrabCut from a manually supplied polygon in source pixel coordinates."""
import argparse
import json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', required=True)
    p.add_argument('--polygon', required=True, help='JSON array of [x,y] points, original image pixels')
    p.add_argument('--output', required=True, help='Transparent PNG')
    p.add_argument('--band', type=int, default=25, help='Uncertain contour band, source pixels')
    a = p.parse_args()
    if a.band < 1 or Path(a.output).suffix.lower() != '.png':
        p.error('band must be positive; output must be .png')
    src = Image.open(a.input).convert('RGB')
    points = json.loads(Path(a.polygon).read_text())
    if len(points) < 3:
        p.error('polygon requires at least three points')
    mask = Image.new('L', src.size)
    ImageDraw.Draw(mask).polygon([tuple(v) for v in points], fill=255)
    b = np.array(mask)
    kernel = np.ones((a.band, a.band), np.uint8)
    labels = np.where(b > 0, 3, 2).astype('uint8')
    labels[cv2.erode(b, kernel) > 0] = 1
    labels[cv2.dilate(b, kernel) == 0] = 0
    if not np.any(labels == 1) or not np.any(labels == 0):
        p.error('polygon/band must leave definite foreground and background')
    cv2.setNumThreads(2)
    cv2.grabCut(cv2.cvtColor(np.array(src), cv2.COLOR_RGB2BGR), labels, None,
                np.zeros((1,65)), np.zeros((1,65)), 3, cv2.GC_INIT_WITH_MASK)
    alpha = Image.fromarray(np.where((labels == 1) | (labels == 3), 255, 0).astype('uint8'))
    alpha = alpha.filter(ImageFilter.GaussianBlur(.7))
    out = src.convert('RGBA'); out.putalpha(alpha)
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    out.crop(alpha.getbbox()).save(a.output)

if __name__ == '__main__':
    main()
