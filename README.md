# CrossStitch

Testing out making a cross-stitch template generator

DMC conversion table comes from [bmanturner](https://github.com/bmanturner/hex-dmc/blob/master/est_dmc_hex.txt)

## Dependencies

[Pillow](https://pypi.org/project/Pillow/), [progress](https://pypi.org/project/progress/)

`pip install pillow progress`

## Example Usage

Input image:
![Source Image](sample_images/stardew.png)

With a specified width of `500` and `10` max DMC colors:

Output DMC-only image:
![1-to-1, DMC colors only](doc/dmc_image.png)

Cross-stitch template:
![Cross-stitch template (also outputs one with a white background instead of the source image)](doc/cross-stitch.png)

Index key:

```plaintext:docs/key.txt

```
