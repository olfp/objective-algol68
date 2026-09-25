# objective-algol68
A vibe coded try at Objective Algol68.

## Convert `.a68` to Unicode-stropped `.u68`

`a2u.py` converts upper-stropped Algol 68 source into Unicode-stropped source:

- all-uppercase words become Mathematical Bold (for example `MODE` → `𝖬𝖮𝖣𝖤`);
- all-lowercase identifiers become Mathematical Italic (for example `shape` → `𝑠ℎ𝑎𝑝𝑒`);
- comments, string literals, digits, punctuation, and operators are preserved;
- mixed-case identifiers are left unchanged.

The default output replaces `.a68` with `.u68`:

```sh
python3 a2u.py shapesmod.a68
```

To choose an output path:

```sh
python3 a2u.py shapesmod.a68 --output shapesmod.u68
```

To write to standard output:

```sh
python3 a2u.py shapesmod.a68 --stdout
```

Run the converter tests with:

```sh
python3 -m unittest discover -v
```
