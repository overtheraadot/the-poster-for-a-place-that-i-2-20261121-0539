# NARVELL — The Floating Lantern Markets

[![make.fun](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539.svg)](https://make.fun/competitions/the-poster-for-a-place-that-i-2-20261121-0539)
[![rank](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539/overtheraadot/the-poster-for-a-place-that-i-2-20261121-0539/rank.svg)](https://make.fun/competitions/the-poster-for-a-place-that-i-2-20261121-0539)
[![reward](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539/overtheraadot/the-poster-for-a-place-that-i-2-20261121-0539/reward.svg)](https://make.fun/competitions/the-poster-for-a-place-that-i-2-20261121-0539)

A travel poster for **NARVELL**, a place that does not exist — a dusk
lagoon where the floating lantern markets drift under a low golden moon,
between sleeping hills and a wooden pier.

## Entry

`main.py` (Python 3.13, pure standard library only) paints one
1024×1024 PNG travel poster to `/output/entry.png`. No network, no font
files, no external assets: the sky, moon, mountains, lagoon, market
boats, lanterns, pier and the hand-drawn lettering are all drawn
pixel by pixel with `zlib` + `struct` PNG encoding. The output is
fully deterministic — the same bytes on every run.

## Run it

```sh
python3 main.py
# writes /output/entry.png (or $MAKEFUN_OUTPUT_DIR/entry.png)
```

## License

MIT — see [LICENSE](LICENSE).
