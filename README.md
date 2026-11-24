# OpenJDK 17 AVX-512 Base64 tail probe

This small PoC measures a **logical output boundary violation** in the Base64 decoder of a pinned OpenJDK 17 build. It decodes `A` repeated 128 times followed by `=` into a real, 160-byte Java array filled with a guard byte. The calculated output length is 98 bytes. On the tested Temurin 17.0.6+10 build, 62 guard bytes at offsets 98–159 changed; the decoder then rejected the malformed input.

All writes observed by **this probe** remain inside its allocated 160-byte array. This result alone does **not** demonstrate a Java heap out-of-bounds write, information disclosure, command execution, or an exploit against Jenkins or another application.

## Reproduce

Requirements: Docker with Compose, Python 3, x86-64 Linux containers, and AVX-512 features exposed to the container. The host used for this measurement exposed AVX-512 BW/VBMI and BMI2. `-XX:UseAVX=3` requests the relevant JVM path but cannot add CPU features missing from the host.

```sh
python verify.py
```

The script builds two images from pinned Eclipse Temurin archives, verifies their SHA-256 values, and runs three cases:

| Case | Expected changed bytes at offsets 98–159 |
| --- | ---: |
| 17.0.6+10, Base64 intrinsic enabled | 62 |
| 17.0.5+8 | 0 |
| 17.0.6+10, `-XX:-UseBASE64Intrinsics` | 0 |

A fresh build and run on 2026-11-24 produced `62 / 0 / 0` changed bytes in that order. All three runs ended with `IllegalArgumentException` for the malformed input.

Exit code `0` means these measured results match. Exit code `2` means the 17.0.6+10 run changed no guard bytes, so the result is inconclusive on that host. Other mismatches return `1`. To repeat without downloading the JDKs again, run `python verify.py --skip-build`.

The individual cases can also be run with `docker compose run --rm jdk17_0_6`, `docker compose run --rm jdk17_0_5`, and `docker compose run --rm jdk17_0_6_no_intrinsics`.

## Scope

This repository publishes only the bounded array measurement and its two controls. It does not claim that every build from 17.0.6 onward is affected. The observed behavior is consistent with the [AVX-512 Base64 decoder change introduced in jdk17u](https://github.com/openjdk/jdk17u/commit/07050b000ce20350c55505fbc5595c0b6c3052b5); that source comparison is separate from this dynamic measurement.
