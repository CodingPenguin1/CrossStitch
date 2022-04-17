#!/usr/bin/env python
from os.path import join
from tkinter import filedialog as fd
from PIL import Image, ImageDraw
import turtle
from progress.bar import IncrementalBar


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
    # === USER INPUT === #
    filepath = fd.askopenfilename(title='Input image',
                                  filetypes=[('PNG', '*.png'), ('JPEG', '*.jpg')])

    desired_width = int(turtle.textinput('Cross Stitch Size', 'How many stitches wide would you like it to be?'))
    if desired_width < 0:
        raise ValueError('Width must be positive')

    # Must be no bigger than 256 (https://stackoverflow.com/questions/37146711/im-getcolors-returns-none)
    max_colors = int(turtle.textinput('DMC Color Count', 'How many DMC colors would you like to limit the image to? Note: final value may be lower than you specify.'))
    if max_colors < 1 or max_colors > 256:
        raise ValueError('DMC color count must be between 1 and 256')

    # === DOWNSCALING AND CONVERTING TO DMC COLORS === #
    with Image.open(filepath) as original_image:
        # Downscale with bilinear interpolation
        height = int((desired_width / original_image.width) * original_image.height)
        downscaled_image = original_image.resize((desired_width, height), resample=2)

        scaledown_color_count = max_colors
        while True:
            # Downsample to a lower colorspace
            pixelated_image = downscaled_image.convert(mode='P', palette=Image.ADAPTIVE, colors=scaledown_color_count)

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

            if len(dmc_table) == max_colors:
                break
            else:
                scaledown_color_count += 1
            if scaledown_color_count == 256:
                break

        print(f'Scaling {scaledown_color_count} RGB colors to {len(dmc_table)} DMC colors')

        # Reindex DMC table
        for i in range(len(dmc_table)):
            dmc_table[i][0] = i

        # Rewrite pixel values to match DMC values
        dmc_image = Image.new(mode='P', size=pixelated_image.size, color=0)
        with IncrementalBar('Converting to DMC colors', max=dmc_image.width * dmc_image.height, suffix='%(percent)d%%') as bar:
            for x in range(dmc_image.width):
                for y in range(dmc_image.height):
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
                    dmc_image.putpixel((x, y), closest_dmc_rgb)
                    bar.next()

        # Update color list and palette since we just changed the pixel values
        colors = dmc_image.getcolors()  # [(count, index), ...]
        palette = dmc_image.palette.colors  # {color: index, ...}

        # === GENERATE OUTPUT IMAGES === #
        # Upscale so we can put numbers on each pixel
        UPSCALE_FACTOR = 26
        pixelated_upscaled = dmc_image.resize((dmc_image.size[0] * UPSCALE_FACTOR, dmc_image.size[1] * UPSCALE_FACTOR), 0)

        # Create template file (white with black text and lines, no image)
        template_image = Image.new('RGB', pixelated_upscaled.size, color='white')
        template_draw = ImageDraw.Draw(template_image)

        # Draw numbers on each pixel
        draw = ImageDraw.Draw(pixelated_upscaled)
        with IncrementalBar('Drawing indicies', max=dmc_image.width * dmc_image.height, suffix='%(percent)d%%') as bar:
            for x in range(dmc_image.width):
                for y in range(dmc_image.height):
                    draw_coord = (x * UPSCALE_FACTOR + 4, y * UPSCALE_FACTOR + 1)  # Text characters are default 6x6

                    # Get index from DMC list
                    rgb_index = dmc_image.getpixel((x, y))
                    dmc_rgb_value = next((key for key in palette if palette[key] == rgb_index), None)
                    dmc_index = next((i for i in range(len(dmc_table)) if dmc_table[i][3] == dmc_rgb_value), None)

                    # Determine if text should be white or black
                    fill = 'white' if sum(dmc_rgb_value) / len(dmc_rgb_value) < 127 else 'black'
                    draw.text(draw_coord, str(dmc_index), anchor='mm', fill=fill)
                    template_draw.text(draw_coord, str(dmc_index), anchor='mm', fill='black')
                    bar.next()

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
        dmc_image_filepath = join('output', 'dmc_image.png')
        dmc_image.save(dmc_image_filepath)
        print(f'Downscaled image written to {dmc_image_filepath}')

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
