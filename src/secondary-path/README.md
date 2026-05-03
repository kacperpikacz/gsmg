# Secondary Path

This path starts from the second creator hint: a Decentraland screenshot.

## Clue

On 2020-02-20, the creator shared a screenshot from Decentraland. The scene points to coordinates:

```text
-41,-17
```

At that location there is a large question mark. Interacting with the bottom of it plays a hiss/white-noise sound.

## Get The Audio

Using Decentraland tooling, inspect the parcel:

```bash
dcl status -41,-17
```

The parcel references:

```text
puzzlepiece.mp3
QmeRy5MjmEZ2W6J3DwhQfht5HKBKXBFpoGzSkzmjeGKiDK
```

Download it from the Decentraland content API:

```bash
curl https://peer.decentraland.org/content/contents/QmeRy5MjmEZ2W6J3DwhQfht5HKBKXBFpoGzSkzmjeGKiDK > puzzlepiece.mp3
```

## Decode The Audio

The audio has left and right channels. Invert one channel, combine it with the other, then inspect the spectrogram.

```python
import numpy as np
import soundfile as sf
import matplotlib.pyplot as plt

data, samplerate = sf.read("puzzlepiece.mp3")
left = data[..., 0]
right = data[..., 1]

new_right = np.array([(-1 ** i) * x for i, x in enumerate(right)])
mono = left + new_right

plt.figure(figsize=(15, 5))
plt.specgram(mono, Fs=samplerate)
plt.show()
```

The spectrogram reveals hex-like numbers:

```text
48 41 53 48 54 48 45 54 45 58 54
```

Decode as hex ASCII:

```python
numbers = ["48", "41", "53", "48", "54", "48", "45", "54", "45", "58", "54"]
print("".join(chr(int(n, 16)) for n in numbers))
```

Result:

```text
HASHTHETEXT
```

## Hash The Text

Hash all text from the original image, including the Bitcoin address:

```text
GSMGIO5BTCPUZZLECHALLENGE1GSMG1JC9wtdSwfwApgj2xcmJPAwx7prBe
```

```python
import hashlib

text = "GSMGIO5BTCPUZZLECHALLENGE1GSMG1JC9wtdSwfwApgj2xcmJPAwx7prBe"
print(hashlib.sha256(text.encode()).hexdigest())
```

Output:

```text
89727c598b9cd1cf8873f27cb7057f050645ddb6a7a157a110239ac0152f6a32
```

## Result

The secondary path URL is:

```text
https://gsmg.io/89727c598b9cd1cf8873f27cb7057f050645ddb6a7a157a110239ac0152f6a32
```

This page is the SalPhaseIon / Cosmic Duality secondary door.
