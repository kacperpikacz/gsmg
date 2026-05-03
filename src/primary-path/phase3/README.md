# Phase 3

Phase 3 is not stored as a separate HTML file in this repo.

It is the second encrypted OpenSSL blob inside:

```text
primary-path/phase2/phase.html
```

The Phase 3 password is made by joining the seven solved Phase 2.1 parts exactly:

```text
causality
Safenet
Luna
HSM
11110
0x736B6E616220726F662074756F6C69616220646E6F63657320666F206B6E697262206E6F20726F6C6C65636E61684320393030322F6E614A2F33302073656D695420656854
B5KR/1r5B/2R5/2b1p1p1/2P1k1P1/1p2P2p/1P2P2P/3N1N2 b - - 0 1
```

Joined password:

```text
causalitySafenetLunaHSM111100x736B6E616220726F662074756F6C69616220646E6F63657320666F206B6E697262206E6F20726F6C6C65636E61684320393030322F6E614A2F33302073656D695420656854B5KR/1r5B/2R5/2b1p1p1/2P1k1P1/1p2P2p/1P2P2P/3N1N2 b - - 0 1
```

SHA-256 of the joined password:

```text
1a57c572caf3cf722e41f5f9cf99ffacff06728a43032dd44c481c77d2ec30d5
```

Use that digest as the OpenSSL password to decrypt the second blob.

The decrypted Phase 3 text starts:

```text
What if the merovingian is wrong. What instead of causality something else could be ours?
```

It then gives three clues for the next Phase 3.2 encrypted blob.

## Phase 3.2

The three Phase 3 clues resolve to:

```text
jacquefresco
giveitjustonesecond
heisenbergsuncertaintyprinciple
```

Joined password:

```text
jacquefrescogiveitjustonesecondheisenbergsuncertaintyprinciple
```

SHA-256 of that joined password:

```text
250f37726d6862939f723edc4f993fde9d33c6004aab4f2203d9ee489d61ce4c
```

Use that digest as the OpenSSL password to decrypt the Phase 3.2 blob.

The Phase 3 API decrypts this dynamically from the Phase 2 source HTML chain.
