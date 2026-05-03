# Phase 0

Phase 0 starts with the initial puzzle image:

```text
primary-path/phase0/puzzle.png
```

The first hint was:

```text
follow the white rabbit
```

## Grid

The image is a 14x14 grid with four colors:

```text
white
black
yellow
blue
```

Reading counter-clockwise from the top-left corner, the colored squares line up every 8 positions.

That suggests bytes:

```text
8 bits = 1 byte
```

## Reading Order

Read the grid in a counter-clockwise spiral:

```text
left side down
bottom left to right
right side up
top right to left
repeat inward
```

This produces byte-like chunks:

```text
0110011b
0111001b
0110110b
0110011b
0010111y
0110100b
0110111b
0010111b
0111010y
0110100y
0110010b
0111001b
0110010b
0110010b
0110010y
0110100b
0111001b
0111000y
0110110y
0110000b
0110111y
0111010y
0110010b
0110010y
```

## Color Values

Assume:

```text
white = 0
black = 1
```

The first bytes then start to look like ASCII. Testing the remaining colors gives:

```text
blue = 1
yellow = 0
```

So:

```text
b = 1
y = 0
```

## Decoded Message

After replacing `b` with `1` and `y` with `0`, decode the binary as ASCII:

```text
gsmg.io/theseedisplanted
```

That is the URL for Phase 1:

```text
https://gsmg.io/theseedisplanted
```

## Notes

This phase teaches the first useful rules:

```text
read unusual layouts carefully
group binary-looking data into bytes
URLs are part of the puzzle trail
```
