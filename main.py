#!/usr/bin/env python
from os.path import join

import pandas as pd
from PIL import Image, ImageDraw

MAX_COLORS = 6  # Must be no bigger than 256 (https://stackoverflow.com/questions/37146711/im-getcolors-returns-none)
DESIRED_WIDTH = 100


def distance(point_a, point_b):
    return sum((point_a[i] - point_b[i]) ** 2 for i in range(len(point_a)))**0.5


def get_dmc(rgb):
    df = pd.read_csv('dmc.csv')
    closest_row_index, best_difference = 0, float('inf')
    for i, row in df.iterrows():
        dmc_rgb = (row['red'], row['green'], row['blue'])
        difference = distance(rgb, dmc_rgb)
        if difference < best_difference:
            best_difference = difference
            closest_row_index = i
    return df.iloc[closest_row_index][0], df.iloc[closest_row_index][4]


if __name__ == '__main__':
    with Image.open(join('source_images', 'bills.png')) as image:
        # Downscale with bilinear interpolation
        height = int((DESIRED_WIDTH / image.width) * image.height)
        image = image.resize((DESIRED_WIDTH, height), resample=2)

        # Downsample to a lower colorspace
        pixelated_image = image.convert(mode='P', palette=1, colors=MAX_COLORS)

        # Upscale so we can put numbers on each pixel
        UPSCALE_FACTOR = 13
        pixelated_upscaled = image.resize((image.size[0] * UPSCALE_FACTOR, image.size[1] * UPSCALE_FACTOR), 0)

        # Draw numbers on each pixel
        draw = ImageDraw.Draw(pixelated_upscaled)
        for x in range(pixelated_image.width):
            for y in range(pixelated_image.height):
                draw_coord = (x * UPSCALE_FACTOR + 4, y * UPSCALE_FACTOR + 1)  # Text characters are default 6x6
                index = str(pixelated_image.getpixel((x, y)))
                draw.text(draw_coord, index, anchor='mm', fill='black')

        # Draw lines between every pixel
        for x in range(UPSCALE_FACTOR - 1, pixelated_upscaled.width, UPSCALE_FACTOR):
            draw.rectangle([(x, 0), (x + 1, pixelated_upscaled.height)], fill='black')
        for y in range(UPSCALE_FACTOR - 1, pixelated_upscaled.height, UPSCALE_FACTOR):
            draw.rectangle([(0, y), (pixelated_upscaled.width, y + 1)], fill='black')

        # Draw bigger lines between every 10 pixels
        for x in range(10 * UPSCALE_FACTOR - 1, pixelated_upscaled.width, UPSCALE_FACTOR * 10):
            draw.rectangle([(x - 1, 0), (x + 2, pixelated_upscaled.height)], fill='black')
        for y in range(10 * UPSCALE_FACTOR - 1, pixelated_upscaled.height, UPSCALE_FACTOR * 10):
            draw.rectangle([(0, y - 1), (pixelated_upscaled.width, y + 2)], fill='black')

        # Generate DMC color key
        dmc_table = []  # [[index, DMC code, DMC name, RGB, count], ...]
        colors = pixelated_image.getcolors()  # [(count, index), ...]
        palette = pixelated_image.palette.colors  # {color: index, ...}

        print('{:<8}{:<10}{:<30}{:<18}{:<10}'.format('Index', 'DMC Code', 'DMC Name', 'RGB', 'Count'))
        for count, index in colors:
            rgb = None
            for key in palette:
                if palette[key] == index:
                    rgb = key
            dmc_code, dmc_name = get_dmc(rgb)
            dmc_table.append([index, dmc_code, dmc_name, rgb, count])
            print('{:<8}{:<10}{:<30}{:<18}{:<10}'.format(index, dmc_code, dmc_name, str(rgb), count))

        # Write output files
        downscaled_filepath = join('output', 'downscaled.png')
        pixelated_image.save(downscaled_filepath)
        print(f'Downscaled image written to {downscaled_filepath}')

        cross_stitch_filepath = join('output', 'cross-stitch.png')
        pixelated_upscaled.save(cross_stitch_filepath)
        print(f'Cross-stitch template written to {cross_stitch_filepath}')

        key_filepath = join('output', 'key.txt')
        with open(key_filepath, 'w') as f:
            f.write('{:<8}{:<10}{:<30}{:<18}{:<10}\n'.format('Index', 'DMC Code', 'DMC Name', 'RGB', 'Count'))
            for row in dmc_table:
                index, dmc_code, dmc_name, rgb, count = row
                f.write('{:<8}{:<10}{:<30}{:<18}{:<10}\n'.format(index, dmc_code, dmc_name, str(rgb), count))
        print(f'Key written to {key_filepath}')