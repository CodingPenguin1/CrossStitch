#!/usr/bin/env python
from os.path import join
from tkinter.tix import MAX

from PIL import Image, ImageDraw

MAX_COLORS = 15  # Must be no bigger than 256 (https://stackoverflow.com/questions/37146711/im-getcolors-returns-none)
DESIRED_WIDTH = 100


def distance(point_a, point_b):
    return sum((point_a[i] - point_b[i]) ** 2 for i in range(len(point_a)))**0.5


def get_dmc(rgb):
    # Generate lookup table
    lookup_table = []
    with open('dmc.txt', 'r') as f:
        lines = f.readlines()
        for i in range(0, len(lines), 3):
            dmc_code = lines[i].strip()
            dmc_name = lines[i + 1].strip()
            dmc_hex = lines[i + 2].strip()
            dmc_rgb = tuple(int(dmc_hex[i:i + 2], 16) for i in (0, 2, 4))  # https://stackoverflow.com/questions/29643352/converting-hex-to-rgb-value-in-python
            lookup_table.append([dmc_code, dmc_name, dmc_hex, dmc_rgb])

    # Find closest color to `rgb` in lookup table
    closest_row_index, best_difference = 0, float('inf')
    for i in range(len(lookup_table)):
        dmc_rgb = lookup_table[i][3]
        diff = distance(dmc_rgb, rgb)
        if diff < best_difference:
            closest_row_index, best_difference = i, diff
    return lookup_table[closest_row_index]


if __name__ == '__main__':
    with Image.open(join('source_images', 'bills.png')) as original_image:
        # Downscale with bilinear interpolation
        height = int((DESIRED_WIDTH / original_image.width) * original_image.height)
        downscaled_image = original_image.resize((DESIRED_WIDTH, height), resample=2)

        scaledown_color_count = MAX_COLORS
        while True:
            # Downsample to a lower colorspace
            pixelated_image = downscaled_image.convert(mode='P', palette=Image.ADAPTIVE, colors=scaledown_color_count)
            # pixelated_image.show()

            # Generate DMC color key
            dmc_table = []  # [[index, DMC code, DMC name, RGB, count], ...]
            colors = pixelated_image.getcolors()  # [(count, index), ...]
            palette = pixelated_image.palette.colors  # {color: index, ...}

            for count, index in colors:
                rgb = None
                for key in palette:
                    if palette[key] == index:
                        rgb = key

                _hex = '%02x%02x%02x' % rgb
                dmc_code, dmc_name, dmc_hex, dmc_rgb = get_dmc(rgb)
                dmc_already_used = any(dmc_table[i][1] == dmc_code for i in range(len(dmc_table)))
                if not dmc_already_used:
                    dmc_table.append([index, dmc_code, dmc_name, dmc_rgb, dmc_hex, rgb, _hex, count])

            if len(dmc_table) == MAX_COLORS:
                break
            else:
                scaledown_color_count += 1

        # Reindex DMC table
        for i in range(len(dmc_table)):
            dmc_table[i][0] = i

        # Rewrite pixel values to match DMC values
        for dmc in dmc_table:
            print('\t'.join([str(i) for i in dmc]))
        for x in range(pixelated_image.width):
            for y in range(pixelated_image.height):
                # Get DMC RGB value to set pixel to
                closest_dmc_rgb, best_difference = None, float('inf')
                for dmc in dmc_table:
                    dmc_rgb = dmc[3]
                    rgb_index = pixelated_image.getpixel((x, y))
                    rgb_value = next((key for key in palette if palette[key] == rgb_index), None)
                    diff = distance(dmc_rgb, rgb_value)
                    if diff < best_difference:
                        closest_dmc_rgb, best_difference = dmc[3], diff

                # Set the pixel to the DMC RGB value
                pixelated_image.putpixel((x, y), closest_dmc_rgb)

        # Update color list and palette since we just changed the pixel values
        colors = pixelated_image.getcolors()  # [(count, index), ...]
        palette = pixelated_image.palette.colors  # {color: index, ...}

        # === GENERATE OUTPUT IMAGES === #
        # Upscale so we can put numbers on each pixel
        UPSCALE_FACTOR = 26
        pixelated_upscaled = downscaled_image.resize((downscaled_image.size[0] * UPSCALE_FACTOR, downscaled_image.size[1] * UPSCALE_FACTOR), 0)

        # Create template file (white with black text and lines, no image)
        template_image = Image.new('RGB', pixelated_upscaled.size, color='white')
        template_draw = ImageDraw.Draw(template_image)

        # Draw numbers on each pixel
        draw = ImageDraw.Draw(pixelated_upscaled)
        for x in range(pixelated_image.width):
            for y in range(pixelated_image.height):
                draw_coord = (x * UPSCALE_FACTOR + 4, y * UPSCALE_FACTOR + 1)  # Text characters are default 6x6

                # Get index from DMC list
                rgb_index = pixelated_image.getpixel((x, y))
                dmc_rgb_value = None
                dmc_index = None
                for key in palette:
                    if palette[key] == rgb_index:
                        dmc_rgb_value = key
                        break
                for i in range(len(dmc_table)):
                    if dmc_table[i][3] == dmc_rgb_value:
                        dmc_index = i
                        break

                draw.text(draw_coord, str(dmc_index), anchor='mm', fill='black')
                template_draw.text(draw_coord, str(dmc_index), anchor='mm', fill='black')

        # Draw lines between every pixel
        for x in range(UPSCALE_FACTOR - 1, pixelated_upscaled.width, UPSCALE_FACTOR):
            draw.rectangle([(x, 0), (x + 1, pixelated_upscaled.height)], fill='black')
            template_draw.rectangle([(x, 0), (x + 1, pixelated_upscaled.height)], fill='black')
        for y in range(UPSCALE_FACTOR - 1, pixelated_upscaled.height, UPSCALE_FACTOR):
            draw.rectangle([(0, y), (pixelated_upscaled.width, y + 1)], fill='black')
            template_draw.rectangle([(0, y), (pixelated_upscaled.width, y + 1)], fill='black')

        # Draw bigger lines between every 10 pixels
        for x in range(10 * UPSCALE_FACTOR - 1, pixelated_upscaled.width, UPSCALE_FACTOR * 10):
            draw.rectangle([(x - 1, 0), (x + 2, pixelated_upscaled.height)], fill='black')
            template_draw.rectangle([(x - 1, 0), (x + 2, pixelated_upscaled.height)], fill='black')
        for y in range(10 * UPSCALE_FACTOR - 1, pixelated_upscaled.height, UPSCALE_FACTOR * 10):
            draw.rectangle([(0, y - 1), (pixelated_upscaled.width, y + 2)], fill='black')
            template_draw.rectangle([(0, y - 1), (pixelated_upscaled.width, y + 2)], fill='black')

        # === WRITE OUTPUT FILES === #
        downscaled_filepath = join('output', 'downscaled.png')
        pixelated_image.save(downscaled_filepath)
        print(f'Downscaled image written to {downscaled_filepath}')

        cross_stitch_filepath = join('output', 'cross-stitch.png')
        pixelated_upscaled.save(cross_stitch_filepath)
        print(f'Cross-stitch written to {cross_stitch_filepath}')

        template_filepath = join('output', 'template.png')
        template_image.save(template_filepath)
        print(f'Template written to {template_filepath}')

        key_filepath = join('output', 'key.txt')
        with open(key_filepath, 'w') as f:
            format_string = '{:<8}{:<10}{:<25}{:<18}{:<10}{:<18}{:<15}{:<15}\n'
            f.write(format_string.format('Index', 'DMC Code', 'DMC Name', 'DMC RGB', 'DMC HEX', 'Actual RGB', 'Actual HEX', 'Count'))
            for row in dmc_table:
                index, dmc_code, dmc_name, dmc_rgb, dmc_hex, rgb, _hex, count = row
                f.write(format_string.format(index, dmc_code, dmc_name, str(dmc_rgb), dmc_hex, str(rgb), _hex, count))
        print(f'Key written to {key_filepath}')
