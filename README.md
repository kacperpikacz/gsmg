# 5 BTC GSMG Puzzle

The GSMG puzzle was a public cryptocurrency puzzle challenge built around a
5 BTC prize. It began with a visual clue and unfolded through several layers of
web pages, hidden messages, cryptography, pop-culture references, and Bitcoin
key material.

At a high level, the puzzle has two roads.

## Primary Road

- **Image stage**
  - The starting image contains a colored grid.
  - Reading the grid in a spiral and converting colors to bits reveals the
    first GSMG URL.

- **Web and lyric stage**
  - The first page contains hidden form behavior and image fragments.
  - The clues point to a music reference, whose lyrics provide the next
    password.

- **OpenSSL stage**
  - The next page contains salted OpenSSL blobs.
  - Matrix-themed clues lead to password material that decrypts the first blob.

- **Seven-part password stage**
  - The decrypted text gives several exact password fragments.
  - These fragments combine references to Matrix lore, HSM terminology,
    Bitcoin history, and chess notation.
  - Joining the fragments and hashing them unlocks the next encrypted layer.

- **Architect / Phase 3.2 stage**
  - The next layer contains another encrypted blob and an Architect-style
    message.
  - The solve chain includes encoding repair, Beaufort decryption, and a
    checkerboard-style numeric cipher.
  - This stage exposes a final OpenSSL/AES blob connected to the remaining
    private-key hunt.

## Secondary Road

- **Decentraland clue**
  - A separate creator hint points to a Decentraland location.
  - The parcel contains an audio clue.

- **Audio/spectrogram stage**
  - The audio is manipulated by channel processing.
  - A spectrogram reveals the instruction `HASHTHETEXT`.

- **Hash door**
  - Hashing the original puzzle text, including the Bitcoin address, reveals
    another GSMG URL.
  - That URL opens the SalPhaseIon / Cosmic Duality page, a secondary branch of
    the puzzle.

## Themes

- visual steganography
- binary and spiral-grid reading
- hidden HTML forms
- OpenSSL salted encryption
- SHA-256 password derivation
- Matrix references
- Bitcoin and private-key clues
- chess/FEN notation
- audio spectrogram analysis
- classical cipher techniques

## Status

The documented solve reaches the Architect / Phase 3.2 material and extracts
the final AES blob. The last private-key/password step remains the unresolved
part in this write-up.
