# Seamless Camouflage Generator v2

`camouflage_generator_v2.py` is a procedural camouflage texture generator written in Python.
It creates **seamless / tileable textures**: the right edge continues into the left edge, and the bottom edge continues into the top edge.

The generator is layer-based. A camouflage consists of:

1. a base color;
2. any number of procedural layers;
3. each layer having its own pattern type, color, scale, density, seed and other settings.

This makes it possible to build woodland, digital, Flecktarn-like, Splittertarn-like, tiger-stripe, desert, snow, urban, leaf, cracked/reptile, hybrid and completely custom patterns from one generator.

---

## 1. Requirements

Python 3.9+ is recommended.

Install dependencies:

```bash
pip install numpy pillow
```

The generator itself is a single file:

```text
camouflage_generator_v2.py
```

---

## 2. Basic usage

Generate one of the built-in presets:

```bash
python camouflage_generator_v2.py --preset woodland --output woodland.png
```

Generate it together with a 3x3 tiled preview:

```bash
python camouflage_generator_v2.py --preset woodland --output woodland.png --preview
```

The preview is saved next to the output image as:

```text
woodland_preview.png
```

The preview is useful for checking whether the pattern repeats naturally and whether the chosen feature size is appropriate.

Generate from a custom JSON configuration:

```bash
python camouflage_generator_v2.py --config my_camo.json --output my_camo.png --preview
```

If both `--preset` and `--config` are given, the JSON configuration is used.

---

## 3. Command-line options

| Option | Meaning | Default |
|---|---|---|
| `--preset NAME` | Use a built-in preset | `woodland` |
| `--config FILE.json` | Load configuration from JSON | none |
| `--output FILE.png` | Output image path | `camouflage.png` |
| `--preview` | Also save a 3x3 tiled preview | off |

Available built-in presets:

```text
woodland
digital
flecktarn
splittertarn
tiger
```

Example:

```bash
python camouflage_generator_v2.py --preset flecktarn --output flecktarn.png --preview
```

---

# 4. Configuration file structure

A minimal configuration looks like this:

```json
{
  "width": 1024,
  "height": 1024,
  "base_color": "#7A8055",
  "layers": [
    {
      "type": "blobs",
      "color": "#415035",
      "coverage": 0.40,
      "scale": 150,
      "seed": 10
    }
  ]
}
```

Top-level settings:

| Parameter | Type | Meaning | Default |
|---|---:|---|---:|
| `width` | integer | Output width in pixels | `1024` |
| `height` | integer | Output height in pixels | `1024` |
| `base_color` | HEX string or RGB array | Background color | `#6B7045` |
| `layers` | array | Procedural layers, applied in order | empty |

Colors may be specified as HEX:

```json
"color": "#4B5434"
```

or as RGB:

```json
"color": [75, 84, 52]
```

Layer order matters. Later layers are painted over earlier layers.

For example:

```json
"layers": [
  { "type": "blobs", "color": "#567044", "seed": 1 },
  { "type": "spots", "color": "#242A20", "seed": 2 }
]
```

The spots are applied on top of the blobs.

---

# 5. Settings common to layers

All layer types use `type` and `color`.
Most also accept `seed`, and every layer accepts `opacity` during compositing.

| Parameter | Meaning | Default |
|---|---|---:|
| `type` | Pattern generator to use | `blobs` |
| `color` | Layer color | required |
| `opacity` | Layer opacity from `0.0` to `1.0` | `1.0` |
| `seed` | Random seed; changes the pattern without changing its style | `0` |

Example:

```json
{
  "type": "blobs",
  "color": "#42513B",
  "opacity": 0.75,
  "seed": 1234
}
```

`seed` is especially useful when you like the parameters but want a different arrangement of shapes.

---

# 6. Pattern types

The generator currently supports:

```text
blobs
organic
blob

digital
pixel
pixels

microdigital
micro-digital
micro_digital

stripes
stripe
tiger

spots
spot
ellipse
ellipses

branches
branch

voronoi

cracks
crack
network

leaves
leaf

brush
brushstroke
brush-stroke
```

The aliases in each group produce the same pattern type.

---

# 7. `blobs` / `organic`

Smooth irregular organic regions created from periodic fractal noise.
This is one of the most useful general-purpose pattern types.

Example:

```json
{
  "type": "blobs",
  "color": "#46563B",
  "coverage": 0.47,
  "scale": 170,
  "aspect": 1.2,
  "angle": 20,
  "octaves": 4,
  "persistence": 0.55,
  "softness": 0.0,
  "seed": 10
}
```

Parameters:

| Parameter | Meaning | Default |
|---|---|---:|
| `coverage` | Approximate fraction of the image covered by the layer | `0.35` |
| `scale` | Approximate feature size in pixels | `120` |
| `aspect` | Elongation factor | `1.0` |
| `angle` | Direction of elongation in degrees | `0` |
| `octaves` | Number of noise scales/detail levels | `3` |
| `persistence` | Strength of progressively smaller detail | `0.55` |
| `softness` | Edge softness; `0` gives hard edges | `0.0` |
| `seed` | Random seed | `0` |

Useful values:

```text
scale = 40..80      small shapes
scale = 100..200    medium shapes
scale = 250..500    large macro shapes

aspect = 1.0        approximately isotropic
aspect = 2.0        elongated
aspect = 4.0        strongly stretched

octaves = 1         very smooth
3..4                natural irregular shapes
5+                  more fine boundary detail
```

Example: large rounded patches:

```json
{
  "type": "blobs",
  "color": "#55633F",
  "coverage": 0.45,
  "scale": 280,
  "aspect": 1.0,
  "octaves": 3,
  "seed": 100
}
```

Example: elongated worm-like shapes:

```json
{
  "type": "blobs",
  "color": "#252B21",
  "coverage": 0.18,
  "scale": 130,
  "aspect": 3.5,
  "angle": 30,
  "octaves": 4,
  "seed": 101
}
```

---

# 8. `digital`

Pixel/block camouflage generated from a periodic low-resolution field and expanded into rectangular cells.

Example:

```json
{
  "type": "digital",
  "color": "#58634B",
  "coverage": 0.45,
  "block_size": 12,
  "scale": 90,
  "aspect": 1.0,
  "angle": 0,
  "octaves": 2,
  "persistence": 0.55,
  "seed": 200
}
```

Parameters:

| Parameter | Meaning | Default |
|---|---|---:|
| `block_size` | Approximate size of individual pixels/blocks in output pixels | `16` |
| `scale` | Size of larger clusters | `block_size * 5` |
| `coverage` | Approximate layer coverage | `0.35` |
| `aspect` | Cluster elongation | `1.0` |
| `angle` | Cluster elongation direction | `0` |
| `octaves` | Number of scales used to form clusters | `2` |
| `persistence` | Fine-detail strength | `0.55` |
| `seed` | Random seed | `0` |

`block_size` is approximate. The generator adjusts the cell grid so it fits the texture dimensions and remains seamless.

Example: coarse digital:

```json
{
  "type": "digital",
  "color": "#384439",
  "block_size": 24,
  "scale": 160,
  "coverage": 0.35,
  "seed": 20
}
```

---

# 9. `microdigital`

`microdigital` uses the same algorithm as `digital`, but supplies smaller defaults.

Default overrides:

```text
block_size = 4
scale      = 26
octaves    = 2
```

All other `digital` parameters are also available.

Example:

```json
{
  "type": "microdigital",
  "color": "#273126",
  "coverage": 0.12,
  "block_size": 3,
  "scale": 20,
  "seed": 300
}
```

This is useful as a micro-pattern on top of large blobs.

---

# 10. `stripes` / `tiger`

Creates periodic stripe patterns. The stripes can be warped with seamless fractal noise.

Example:

```json
{
  "type": "stripes",
  "color": "#263225",
  "kx": 2,
  "ky": 8,
  "coverage": 0.30,
  "warp": 3.1,
  "warp_scale": 100,
  "warp_aspect": 1.0,
  "warp_angle": 0,
  "octaves": 3,
  "persistence": 0.55,
  "softness": 0.0,
  "seed": 501
}
```

Parameters:

| Parameter | Meaning | Default |
|---|---|---:|
| `kx` | Horizontal periodic frequency | `2` |
| `ky` | Vertical periodic frequency | `6` |
| `coverage` | Stripe thickness / approximate covered fraction | `0.30` |
| `warp` | Amount of stripe distortion | `2.5` |
| `warp_scale` | Size of distortion features | `150` |
| `warp_aspect` | Elongation of distortion field | `1.0` |
| `warp_angle` | Direction of distortion field | `0` |
| `octaves` | Distortion detail levels | `3` |
| `persistence` | Distortion fine-detail strength | `0.55` |
| `softness` | Edge softness | `0.0` |
| `seed` | Warp seed | `0` |

`kx` and `ky` are intentionally integer-valued. They define how many phase cycles wrap around the texture and therefore preserve exact periodicity.

Typical tiger-stripe style:

```json
{
  "type": "stripes",
  "color": "#202820",
  "kx": 2,
  "ky": 9,
  "coverage": 0.22,
  "warp": 4.0,
  "warp_scale": 80,
  "seed": 55
}
```

---

# 11. `spots` / `ellipses`

Places many seamless elliptical spots on the toroidal texture.
Spots crossing an edge continue from the opposite side.

Example:

```json
{
  "type": "spots",
  "color": "#2A301E",
  "count": 65,
  "min_radius": 7,
  "max_radius": 25,
  "min_aspect": 0.5,
  "max_aspect": 1.8,
  "irregularity": 0.18,
  "irregularity_scale": 12,
  "softness": 0.0,
  "seed": 102
}
```

Parameters:

| Parameter | Meaning | Default |
|---|---|---:|
| `count` | Number of spots | `30` |
| `min_radius` | Minimum base radius | `10` |
| `max_radius` | Maximum base radius | `50` |
| `min_aspect` | Minimum ellipse aspect ratio | `0.5` |
| `max_aspect` | Maximum ellipse aspect ratio | `2.0` |
| `irregularity` | Noise distortion added to spot boundaries | `0` |
| `irregularity_scale` | Scale of edge distortion | `30` |
| `softness` | Boundary softness | `0` |
| `seed` | Random seed | `0` |

Example: small dot pattern:

```json
{
  "type": "spots",
  "color": "#161B16",
  "count": 180,
  "min_radius": 2,
  "max_radius": 8,
  "min_aspect": 0.7,
  "max_aspect": 1.4,
  "seed": 90
}
```

Example: large elongated islands:

```json
{
  "type": "spots",
  "color": "#604A38",
  "count": 25,
  "min_radius": 25,
  "max_radius": 75,
  "min_aspect": 0.4,
  "max_aspect": 2.8,
  "irregularity": 0.20,
  "irregularity_scale": 20,
  "seed": 91
}
```

---

# 12. `branches`

Produces thin ridge-like branching forms by combining multiple periodic noise fields.
Useful for woodland, vegetation, bark, vein, twig and disruptive line patterns.

Example:

```json
{
  "type": "branches",
  "color": "#1F2E20",
  "coverage": 0.15,
  "scale": 140,
  "branch_scale": 30,
  "aspect": 2.0,
  "angle": 20,
  "octaves": 4,
  "persistence": 0.55,
  "detail_strength": 0.40,
  "softness": 0.0,
  "seed": 123
}
```

Parameters:

| Parameter | Meaning | Default |
|---|---|---:|
| `coverage` | Fraction covered by the branch/ridge network | `0.16` |
| `scale` | Size of the primary branching structure | `120` |
| `branch_scale` | Scale of secondary detail | `35` |
| `aspect` | Elongation of the main structure | `1.5` |
| `angle` | Main elongation direction | `0` |
| `octaves` | Main structure detail levels | `4` |
| `persistence` | Fine-detail strength | `0.55` |
| `detail_strength` | Amount of secondary fine structure | `0.30` |
| `softness` | Edge softness | `0.0` |
| `seed` | Random seed | `0` |

Suggested coverage:

```text
0.05  sparse thin structure
0.10  light branching
0.15  moderate
0.25  dense
0.35  very dense
```

---

# 13. `voronoi`

Creates seamless Voronoi regions.
It can generate either filled cells or cell boundaries.

## 13.1 Filled-cell mode

```json
{
  "type": "voronoi",
  "mode": "cells",
  "color": "#69704B",
  "count": 40,
  "coverage": 0.40,
  "seed": 410
}
```

Parameters:

| Parameter | Meaning | Default |
|---|---|---:|
| `count` | Number of Voronoi seed points / approximate cell count | `45` |
| `mode` | `cells` or `edges` | `cells` |
| `coverage` | Fraction of cells selected for the layer | `0.35` |
| `seed` | Random seed | `0` |

In `cells` mode, complete cells are randomly selected. `coverage` therefore controls the probability that a cell belongs to the layer; the final pixel fraction is approximate rather than exact.

## 13.2 Edge mode

```json
{
  "type": "voronoi",
  "mode": "edges",
  "color": "#252A22",
  "count": 70,
  "edge_width": 5,
  "seed": 420
}
```

Additional parameter:

| Parameter | Meaning | Default |
|---|---|---:|
| `edge_width` | Width threshold of cell borders in pixels | `8.0` |

Approximate cell sizes:

```text
count = 15..30     very large polygons
count = 40..80     medium polygons
count = 100..250   small polygons
```

---

# 14. `cracks`

Produces a seamless network along Voronoi boundaries.
Useful for cracked, reptilian, bark-like or net patterns.

Example:

```json
{
  "type": "cracks",
  "color": "#25281F",
  "count": 80,
  "width": 3,
  "roughness": 1.2,
  "rough_scale": 25,
  "seed": 500
}
```

Parameters:

| Parameter | Meaning | Default |
|---|---|---:|
| `count` | Approximate number of cells forming the network | `70` |
| `width` | Width threshold of the cracks | `2.5` |
| `roughness` | Distortion of the otherwise clean cell boundaries | `0.0` |
| `rough_scale` | Scale of crack-edge distortion | `25` |
| `seed` | Random seed | `0` |

Examples:

```text
count = 25, width = 5    large thick network
count = 80, width = 3    medium network
count = 200, width = 1.5 fine network
```

---

# 15. `leaves`

Places pointed leaf-like shapes on the seamless tile.
Each leaf receives a random position and rotation.

Example:

```json
{
  "type": "leaves",
  "color": "#30452D",
  "count": 55,
  "min_length": 30,
  "max_length": 100,
  "min_width": 8,
  "max_width": 28,
  "pointiness": 0.7,
  "veins": false,
  "seed": 300
}
```

Parameters:

| Parameter | Meaning | Default |
|---|---|---:|
| `count` | Number of leaves | `30` |
| `min_length` | Minimum leaf length | `35` |
| `max_length` | Maximum leaf length | `90` |
| `min_width` | Minimum leaf width | `10` |
| `max_width` | Maximum leaf width | `28` |
| `pointiness` | Controls how the leaf narrows toward its ends | `0.65` |
| `veins` | Add a central line inside each leaf | `false` |
| `vein_width` | Half-width threshold of the central vein | `1.5` |
| `seed` | Random seed | `0` |

Note: in the current implementation, `veins` are merged into the same mask and therefore use the same layer color as the leaf itself. To produce differently colored veins, use an additional layer or extend the generator with separate leaf/vein masks.

---

# 16. `brush`

Generates capsule-like brush strokes with random position, size and orientation around a specified main angle.

Example:

```json
{
  "type": "brush",
  "color": "#343D2B",
  "count": 40,
  "min_length": 100,
  "max_length": 300,
  "min_width": 12,
  "max_width": 35,
  "angle": 30,
  "angle_jitter": 20,
  "roughness": 0.15,
  "rough_scale": 15,
  "seed": 400
}
```

Parameters:

| Parameter | Meaning | Default |
|---|---|---:|
| `count` | Number of strokes | `24` |
| `min_length` | Minimum stroke length | `70` |
| `max_length` | Maximum stroke length | `220` |
| `min_width` | Minimum stroke width | `8` |
| `max_width` | Maximum stroke width | `30` |
| `angle` | Main stroke direction in degrees | `0` |
| `angle_jitter` | Random deviation around the main angle | `35` |
| `roughness` | Removes parts of strokes according to seamless noise | `0.0` |
| `rough_scale` | Scale of that noise | `18` |
| `seed` | Random seed | `0` |

For example:

```text
angle = 60
angle_jitter = 8
```

produces mostly parallel strokes approximately from 52° to 68°.

`roughness` in this implementation is a threshold against a normalized random field rather than a conventional 0..1 blend amount. Small values such as `0.05..0.30` usually give the most useful results.

---

# 17. `opacity`

Every layer can have:

```json
"opacity": 0.6
```

Examples:

```text
1.0  fully opaque
0.75 strong
0.5  half transparent
0.2  subtle tint
0.0  invisible
```

The layer is blended over all previous layers.

Opacity is useful for soft color variation, but classic textile camouflage usually looks more natural with mostly opaque layers and deliberately chosen colors.

---

# 18. Important parameter relationships

## `scale` versus image size

`scale` is specified in pixels.
Therefore a configuration designed for 1024x1024 will look finer if rendered at 4096x4096 without adjusting the scale.

If you double the output dimensions and want approximately the same visual proportions, also double size-related parameters such as:

```text
scale
block_size
radius
length
width
warp_scale
branch_scale
rough_scale
```

For example, changing:

```json
"width": 1024,
"height": 1024,
"scale": 160
```

to 2048x2048 while keeping the same relative pattern size suggests:

```json
"width": 2048,
"height": 2048,
"scale": 320
```

## `coverage`

`coverage` is normally in the range:

```text
0.0 ... 1.0
```

For noise-threshold patterns, it approximates the pixel coverage of that layer before later layers overwrite it.

A camouflage with three layers each using `coverage = 0.4` does **not** mean the final image contains 40% of each color. Layers overlap and later layers replace earlier ones.

## `seed`

Changing only the seed:

```json
"seed": 100
```

to:

```json
"seed": 101
```

creates a new pattern with the same general style.

Use different seeds for different layers unless you intentionally want correlated structures.

---

# 19. Seamless tiling

The generator treats the image like the surface of a torus:

```text
left  <-> right
top   <-> bottom
```

Noise fields are periodic, and shape generators calculate toroidal distances where necessary.

Therefore a shape crossing the right border can continue from the left border, and a shape crossing the bottom can continue from the top.

Always inspect the 3x3 preview:

```bash
python camouflage_generator_v2.py --config my.json --output my.png --preview
```

Look especially for:

- visible straight seams;
- sudden changes in feature density;
- features that appear too regularly at the tile period;
- very large shapes whose repetition becomes obvious.

A mathematically seamless texture may still have an obvious *visual repetition* if the tile is too small or contains a very distinctive large feature. Increasing `width`/`height` or adding more independent layers reduces this effect.

---

# 20. Built-in woodland example

```json
{
  "width": 1024,
  "height": 1024,
  "base_color": "#8A8451",
  "layers": [
    {
      "type": "blobs",
      "color": "#46563B",
      "coverage": 0.47,
      "scale": 170,
      "octaves": 4,
      "seed": 10
    },
    {
      "type": "blobs",
      "color": "#5C442C",
      "coverage": 0.26,
      "scale": 105,
      "aspect": 1.4,
      "angle": 30,
      "octaves": 3,
      "seed": 20
    },
    {
      "type": "blobs",
      "color": "#20261E",
      "coverage": 0.15,
      "scale": 65,
      "aspect": 1.7,
      "angle": -25,
      "octaves": 3,
      "seed": 30
    }
  ]
}
```

---

# 21. Built-in digital example

```json
{
  "width": 1024,
  "height": 1024,
  "base_color": "#8F9877",
  "layers": [
    {
      "type": "digital",
      "color": "#58634B",
      "coverage": 0.48,
      "block_size": 14,
      "scale": 95,
      "seed": 100
    },
    {
      "type": "digital",
      "color": "#343D32",
      "coverage": 0.27,
      "block_size": 10,
      "scale": 55,
      "seed": 200
    },
    {
      "type": "microdigital",
      "color": "#B0AA88",
      "coverage": 0.13,
      "block_size": 4,
      "scale": 26,
      "seed": 300
    }
  ]
}
```

---

# 22. German Flecktarn-inspired example

This preset is intended to reproduce the general visual logic of a multi-color German Flecktarn-style pattern rather than an exact manufacturing print.

```json
{
  "width": 1024,
  "height": 1024,
  "base_color": "#7F7A52",
  "layers": [
    {
      "type": "blobs",
      "color": "#4B5434",
      "coverage": 0.48,
      "scale": 125,
      "octaves": 4,
      "persistence": 0.52,
      "seed": 101
    },
    {
      "type": "spots",
      "color": "#2E3A27",
      "count": 95,
      "min_radius": 6,
      "max_radius": 24,
      "min_aspect": 0.55,
      "max_aspect": 1.7,
      "irregularity": 0.14,
      "irregularity_scale": 12,
      "seed": 102
    },
    {
      "type": "spots",
      "color": "#6B4935",
      "count": 78,
      "min_radius": 5,
      "max_radius": 20,
      "min_aspect": 0.6,
      "max_aspect": 1.6,
      "irregularity": 0.16,
      "irregularity_scale": 10,
      "seed": 103
    },
    {
      "type": "spots",
      "color": "#1C211A",
      "count": 70,
      "min_radius": 3,
      "max_radius": 13,
      "min_aspect": 0.7,
      "max_aspect": 1.5,
      "seed": 104
    },
    {
      "type": "spots",
      "color": "#A39A72",
      "count": 42,
      "min_radius": 4,
      "max_radius": 11,
      "min_aspect": 0.8,
      "max_aspect": 1.4,
      "seed": 105
    }
  ]
}
```

Run the built-in version directly:

```bash
python camouflage_generator_v2.py --preset flecktarn --output flecktarn.png --preview
```

---

# 23. German Splittertarn-inspired example

This style uses large angular fields and many narrow rain-like strokes.

```json
{
  "width": 1024,
  "height": 1024,
  "base_color": "#A49D73",
  "layers": [
    {
      "type": "voronoi",
      "mode": "cells",
      "color": "#69704B",
      "count": 34,
      "coverage": 0.42,
      "seed": 410
    },
    {
      "type": "voronoi",
      "mode": "cells",
      "color": "#79563D",
      "count": 30,
      "coverage": 0.24,
      "seed": 420
    },
    {
      "type": "brush",
      "color": "#4D573C",
      "count": 150,
      "min_length": 18,
      "max_length": 42,
      "min_width": 2,
      "max_width": 4,
      "angle": 62,
      "angle_jitter": 7,
      "seed": 430
    }
  ]
}
```

Run:

```bash
python camouflage_generator_v2.py --preset splittertarn --output splittertarn.png --preview
```

---

# 24. Tiger-stripe example

```json
{
  "width": 1024,
  "height": 1024,
  "base_color": "#69724E",
  "layers": [
    {
      "type": "stripes",
      "color": "#263225",
      "kx": 2,
      "ky": 8,
      "coverage": 0.30,
      "warp": 3.1,
      "warp_scale": 100,
      "seed": 501
    },
    {
      "type": "stripes",
      "color": "#393A29",
      "kx": 2,
      "ky": 6,
      "coverage": 0.16,
      "warp": 4.0,
      "warp_scale": 70,
      "seed": 502
    }
  ]
}
```

---

# 25. Desert camouflage example

```json
{
  "width": 1024,
  "height": 1024,
  "base_color": "#C7B483",
  "layers": [
    {
      "type": "blobs",
      "color": "#9B815D",
      "coverage": 0.35,
      "scale": 190,
      "aspect": 1.3,
      "angle": 15,
      "octaves": 4,
      "seed": 1001
    },
    {
      "type": "blobs",
      "color": "#6F6047",
      "coverage": 0.16,
      "scale": 95,
      "aspect": 1.8,
      "angle": -20,
      "octaves": 3,
      "seed": 1002
    },
    {
      "type": "spots",
      "color": "#DDD0A5",
      "count": 55,
      "min_radius": 4,
      "max_radius": 14,
      "seed": 1003
    }
  ]
}
```

---

# 26. Snow / winter camouflage example

```json
{
  "width": 1024,
  "height": 1024,
  "base_color": "#E7E8E2",
  "layers": [
    {
      "type": "blobs",
      "color": "#B7BDBA",
      "coverage": 0.30,
      "scale": 180,
      "aspect": 1.4,
      "angle": 25,
      "octaves": 4,
      "seed": 1101
    },
    {
      "type": "branches",
      "color": "#5E6664",
      "coverage": 0.12,
      "scale": 120,
      "branch_scale": 30,
      "aspect": 2.5,
      "angle": 20,
      "detail_strength": 0.35,
      "seed": 1102
    },
    {
      "type": "spots",
      "color": "#303736",
      "count": 35,
      "min_radius": 4,
      "max_radius": 18,
      "seed": 1103
    }
  ]
}
```

---

# 27. Urban camouflage example

```json
{
  "width": 1024,
  "height": 1024,
  "base_color": "#919597",
  "layers": [
    {
      "type": "digital",
      "color": "#62686B",
      "coverage": 0.42,
      "block_size": 18,
      "scale": 100,
      "seed": 1201
    },
    {
      "type": "digital",
      "color": "#343A3D",
      "coverage": 0.22,
      "block_size": 10,
      "scale": 60,
      "seed": 1202
    },
    {
      "type": "microdigital",
      "color": "#BEC1C0",
      "coverage": 0.10,
      "block_size": 3,
      "scale": 18,
      "seed": 1203
    }
  ]
}
```

---

# 28. Angular polygon camouflage example

```json
{
  "width": 1024,
  "height": 1024,
  "base_color": "#7B805E",
  "layers": [
    {
      "type": "voronoi",
      "mode": "cells",
      "color": "#48533E",
      "count": 55,
      "coverage": 0.42,
      "seed": 1301
    },
    {
      "type": "voronoi",
      "mode": "cells",
      "color": "#5F4938",
      "count": 65,
      "coverage": 0.27,
      "seed": 1302
    },
    {
      "type": "voronoi",
      "mode": "edges",
      "color": "#252B24",
      "count": 75,
      "edge_width": 3,
      "opacity": 0.75,
      "seed": 1303
    }
  ]
}
```

---

# 29. Reptile / cracked camouflage example

```json
{
  "width": 1024,
  "height": 1024,
  "base_color": "#69714F",
  "layers": [
    {
      "type": "blobs",
      "color": "#485139",
      "coverage": 0.42,
      "scale": 150,
      "octaves": 4,
      "seed": 1401
    },
    {
      "type": "cracks",
      "color": "#232820",
      "count": 95,
      "width": 3,
      "roughness": 0.8,
      "rough_scale": 22,
      "seed": 1402
    },
    {
      "type": "spots",
      "color": "#8B865D",
      "count": 75,
      "min_radius": 3,
      "max_radius": 10,
      "seed": 1403
    }
  ]
}
```

---

# 30. Leaf / vegetation camouflage example

```json
{
  "width": 1024,
  "height": 1024,
  "base_color": "#756F4D",
  "layers": [
    {
      "type": "blobs",
      "color": "#48563B",
      "coverage": 0.40,
      "scale": 180,
      "octaves": 4,
      "seed": 1501
    },
    {
      "type": "leaves",
      "color": "#2F432E",
      "count": 60,
      "min_length": 35,
      "max_length": 95,
      "min_width": 9,
      "max_width": 30,
      "pointiness": 0.65,
      "seed": 1502
    },
    {
      "type": "leaves",
      "color": "#929064",
      "count": 32,
      "min_length": 25,
      "max_length": 70,
      "min_width": 7,
      "max_width": 22,
      "pointiness": 0.8,
      "seed": 1503
    },
    {
      "type": "branches",
      "color": "#252F23",
      "coverage": 0.08,
      "scale": 130,
      "branch_scale": 28,
      "aspect": 2.0,
      "angle": 15,
      "seed": 1504
    }
  ]
}
```

---

# 31. Brush-stroke camouflage example

```json
{
  "width": 1024,
  "height": 1024,
  "base_color": "#878462",
  "layers": [
    {
      "type": "brush",
      "color": "#46513B",
      "count": 40,
      "min_length": 120,
      "max_length": 320,
      "min_width": 18,
      "max_width": 48,
      "angle": 25,
      "angle_jitter": 30,
      "roughness": 0.10,
      "rough_scale": 18,
      "seed": 1601
    },
    {
      "type": "brush",
      "color": "#5C4535",
      "count": 28,
      "min_length": 90,
      "max_length": 240,
      "min_width": 12,
      "max_width": 32,
      "angle": -30,
      "angle_jitter": 25,
      "roughness": 0.12,
      "seed": 1602
    },
    {
      "type": "brush",
      "color": "#242A22",
      "count": 18,
      "min_length": 70,
      "max_length": 180,
      "min_width": 7,
      "max_width": 20,
      "angle": 10,
      "angle_jitter": 45,
      "seed": 1603
    }
  ]
}
```

---

# 32. Hybrid macro + micro camouflage example

This example combines large-scale disruption with medium structures and a micro-pattern.

```json
{
  "width": 2048,
  "height": 2048,
  "base_color": "#908B62",
  "layers": [
    {
      "type": "blobs",
      "color": "#556040",
      "coverage": 0.46,
      "scale": 280,
      "octaves": 4,
      "seed": 10
    },
    {
      "type": "blobs",
      "color": "#66503B",
      "coverage": 0.22,
      "scale": 170,
      "aspect": 1.8,
      "angle": 35,
      "seed": 20
    },
    {
      "type": "branches",
      "color": "#293324",
      "coverage": 0.12,
      "scale": 120,
      "branch_scale": 25,
      "aspect": 2.5,
      "angle": 25,
      "seed": 30
    },
    {
      "type": "spots",
      "color": "#191E18",
      "count": 110,
      "min_radius": 5,
      "max_radius": 20,
      "seed": 40
    },
    {
      "type": "microdigital",
      "color": "#A8A079",
      "coverage": 0.08,
      "block_size": 4,
      "scale": 25,
      "seed": 50
    },
    {
      "type": "brush",
      "color": "#37402D",
      "count": 25,
      "min_length": 100,
      "max_length": 260,
      "min_width": 8,
      "max_width": 22,
      "angle": -20,
      "angle_jitter": 30,
      "seed": 60
    }
  ]
}
```

---

# 33. Designing a pattern from scratch

A practical workflow is to work from large to small structures.

### Step 1: choose a base color

Example:

```json
"base_color": "#8D8961"
```

### Step 2: add macro shapes

Use large `blobs`, large `voronoi` cells, or long `brush` strokes.

```json
{
  "type": "blobs",
  "color": "#536040",
  "coverage": 0.45,
  "scale": 220,
  "seed": 1
}
```

### Step 3: add medium disruption

```json
{
  "type": "blobs",
  "color": "#644B39",
  "coverage": 0.24,
  "scale": 110,
  "aspect": 1.7,
  "angle": 25,
  "seed": 2
}
```

### Step 4: add dark small structures

```json
{
  "type": "spots",
  "color": "#22291F",
  "count": 80,
  "min_radius": 4,
  "max_radius": 16,
  "seed": 3
}
```

### Step 5: optionally add a micro-pattern

```json
{
  "type": "microdigital",
  "color": "#AAA37A",
  "coverage": 0.07,
  "block_size": 3,
  "scale": 18,
  "seed": 4
}
```

This macro -> medium -> small -> micro hierarchy usually produces more convincing results than using many layers of identical feature size.

---

# 34. Practical tuning guide

If the pattern looks too busy:

- reduce layer `coverage`;
- reduce `count` for spots/leaves/brush/Voronoi;
- increase `scale` for blobs;
- increase radius/length while reducing count;
- remove one micro-detail layer.

If the pattern looks too empty:

- increase `coverage`;
- increase `count`;
- add another independent layer;
- decrease `scale` to create more distinct regions.

If everything looks too rounded:

- add `voronoi`;
- add `brush`;
- use `digital`;
- increase spot `irregularity`;
- combine several shape types.

If everything looks too geometric:

- add `blobs`;
- add `branches`;
- warp stripes more strongly;
- use irregular spots.

If repetition is obvious in the tiled preview:

- increase the output texture size;
- use more independent seeds;
- avoid one unique giant spot or stroke;
- distribute structure across multiple feature scales.

---

# 35. Performance notes

`blobs`, `digital`, `microdigital` and `stripes` are based mainly on FFT operations and generally scale well.

Some shape-based layers are more expensive because they repeatedly evaluate distances over the full image:

- `spots`;
- `leaves`;
- `brush`;
- `voronoi`;
- `cracks`.

For example, `voronoi` with hundreds of cells on a 4096x4096 image can require substantial RAM and computation.

A good workflow is:

1. design at 512x512 or 1024x1024;
2. inspect the 3x3 preview;
3. tune colors and proportions;
4. render the final version at larger resolution.

If you scale the final resolution up, remember to scale geometric dimensions as described earlier.

---

# 36. Complete defaults reference

This section lists the defaults exactly as used by `camouflage_generator_v2.py`.

## Top level

```text
width       1024
height      1024
base_color  #6B7045
layers      []
```

## Common compositing

```text
type     blobs
opacity  1.0
```

`color` has no generic fallback inside a layer and should always be supplied.

## Blobs

```text
scale         120
aspect        1.0
angle         0
octaves       3
persistence   0.55
seed          0
coverage      0.35
softness      0.0
```

## Digital

```text
block_size    16
scale         block_size * 5
aspect        1.0
angle         0
octaves       2
persistence   0.55
seed          0
coverage      0.35
```

## Microdigital

The type first supplies these values if they are absent:

```text
block_size    4
scale         26
octaves       2
```

It then uses all normal digital defaults for the remaining parameters.

## Stripes

```text
kx            2
ky            6
warp          2.5
warp_scale    150
warp_aspect   1.0
warp_angle    0
octaves       3
persistence   0.55
seed          0
coverage      0.30
softness      0.0
```

## Spots

```text
count               30
min_radius          10
max_radius          50
min_aspect          0.5
max_aspect          2.0
seed                0
irregularity        0
irregularity_scale  30
softness            0
```

## Branches

```text
scale             120
aspect            1.5
angle             0
octaves           4
persistence       0.55
seed              0
branch_scale      35
detail_strength   0.30
coverage          0.16
softness          0.0
```

## Voronoi

```text
count        45
seed         0
mode         cells
coverage     0.35
edge_width   8.0   # used in edges mode
```

## Cracks

```text
count        70
seed         0
width        2.5
roughness    0.0
rough_scale  25
```

## Leaves

```text
count        30
seed         0
min_length   35
max_length   90
min_width    10
max_width    28
pointiness   0.65
veins        false
vein_width   1.5
```

## Brush

```text
count          24
seed           0
min_length     70
max_length     220
min_width      8
max_width      30
angle          0
angle_jitter   35
roughness      0.0
rough_scale    18
```

---

# 37. Notes and current limitations

1. The generator works in RGB and saves RGB PNG files.
2. There is currently no alpha-channel output mode.
3. There is no built-in GUI; configuration is done through presets or JSON.
4. Layer masks cannot yet directly depend on earlier layer masks. For example, there is not yet a built-in option meaning "place these dots only inside the previous green blobs".
5. `coverage` controls the mask of a layer before subsequent layers are added, so final visible color proportions differ from the individual coverage values.
6. Pattern dimensions are primarily pixel-based rather than physical-unit-based.
7. The patterns are procedurally inspired by camouflage families; presets are not guaranteed to reproduce an official production textile pattern exactly.

---

# 38. Ideas for future extensions

Useful future additions to the generator could include:

- parent/child masks: generate one layer only inside another;
- edge-conditioned layers: place spots specifically along another layer's boundary;
- layer exclusion masks;
- color palette files;
- physical dimensions in mm/cm plus DPI;
- SVG/vector output for selected pattern types;
- anisotropic Voronoi cells;
- polygon splinters independent of Voronoi;
- branch skeleton generators;
- configurable leaf orientation instead of fully random rotation;
- masks loaded from external images;
- palette randomization with controlled color ranges;
- command-line parameter overrides;
- automatic contact-sheet generation for many seeds;
- GUI/editor with live preview.

---

# 39. Quick command reference

Woodland:

```bash
python camouflage_generator_v2.py --preset woodland --output woodland.png --preview
```

Digital:

```bash
python camouflage_generator_v2.py --preset digital --output digital.png --preview
```

Flecktarn-inspired:

```bash
python camouflage_generator_v2.py --preset flecktarn --output flecktarn.png --preview
```

Splittertarn-inspired:

```bash
python camouflage_generator_v2.py --preset splittertarn --output splittertarn.png --preview
```

Tiger-stripe:

```bash
python camouflage_generator_v2.py --preset tiger --output tiger.png --preview
```

Custom configuration:

```bash
python camouflage_generator_v2.py --config config.json --output result.png --preview
```

---

# 40. Recommended starting point for experimentation

For a new camouflage, start with this template:

```json
{
  "width": 1024,
  "height": 1024,
  "base_color": "#89865F",
  "layers": [
    {
      "type": "blobs",
      "color": "#52603F",
      "coverage": 0.45,
      "scale": 180,
      "octaves": 4,
      "seed": 1
    },
    {
      "type": "blobs",
      "color": "#654C39",
      "coverage": 0.23,
      "scale": 100,
      "aspect": 1.7,
      "angle": 25,
      "octaves": 3,
      "seed": 2
    },
    {
      "type": "spots",
      "color": "#242A20",
      "count": 70,
      "min_radius": 4,
      "max_radius": 16,
      "seed": 3
    }
  ]
}
```

Then modify one property at a time and compare the 3x3 previews.

A useful pattern-design hierarchy is:

```text
BASE COLOR
    -> MACRO SHAPES
        -> MEDIUM SHAPES
            -> SMALL CONTRAST FEATURES
                -> OPTIONAL MICRO-PATTERN
```

This keeps the camouflage readable at more than one scale and makes parameter tuning much easier.
