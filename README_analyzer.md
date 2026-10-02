# Camouflage Analyzer / Fitter

This tool analyzes a reference camouflage image and produces a JSON config for `camouflage_generator_v3.py`.

## Install

```bash
pip install numpy pillow opencv-python
```

## Basic usage

```bash
python camouflage_analyzer.py reference.png \
  --output fitted.json \
  --preview fitted.png
```

The analyzer automatically estimates:

- palette size (3–7 colors by default in auto mode)
- palette colors
- approximate color area percentages
- broad/macro region scale
- small spot size and count
- clustering of small spots
- a rough style family: organic, digital, or stripes

For organic patterns it uses `multicolor_blobs` for interlocking macro-regions and `clustered_spots` for small grouped flecks. These two layer types were added to generator v3 specifically because the older independent `blobs + spots` model could not reproduce Flecktarn-like structure well.

## Force palette size

```bash
python camouflage_analyzer.py reference.png --colors 5 -o fitted.json --preview fitted.png
```

## Force a style

```bash
python camouflage_analyzer.py reference.png --style organic -o fitted.json
python camouflage_analyzer.py reference.png --style digital -o fitted.json
python camouflage_analyzer.py reference.png --style stripes -o fitted.json
```

`auto` is the default. If the pattern is ambiguous, the analyzer intentionally falls back to `organic` rather than forcing a bad digital/stripe interpretation.

## Generate from the resulting config

```bash
python camouflage_generator_v3.py --config fitted.json --output result.png --preview
```

The generated texture is seamless/tileable on X and Y.

## Output files

The analyzer writes:

- `fitted.json` — generator config
- `fitted.analysis.json` — measured palette, coverage, style scores and component statistics
- preview PNG if `--preview` is specified

## Important limitation

This is a statistical procedural fitter, not an inverse renderer. It does not recover the exact geometry of the original pattern and does not copy the original texture. It tries to recover the visual grammar: colors, area ratios, macro scale, spot scale, and clustering.

It works best on patterns built from flat colored regions such as Flecktarn, woodland-style organic camouflage, many digital patterns, and stripe patterns. It will be less reliable on photographic camouflage, gradients, highly detailed vegetation, fabric folds/shadows, Multicam-like soft transitions, or patterns whose defining structure is not represented by the generator's layer types.

For photographed fabric, crop a relatively flat, evenly lit area if possible. Shadows and strong textile weave can be mistaken for additional colors.
