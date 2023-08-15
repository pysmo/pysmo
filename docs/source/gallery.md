# Gallery

## Realistic noise

Given the spectral amplitude in observed seismic noise on Earth is not flat (i.e. white
noise), it makes sense to calculate more realistic noise for things like resolution tests
with synthetic data.

In this example, random noise seismograms are generated from three different noise
models. These are Peterson's NLNM, NHNM, and an interpolated model that lies between the
two.


![peterson](../examples/tools/noise/peterson.png)

:::{dropdown} {octicon}`code;1em;sd-text-info` View Source Code
:animate: fade-in-slide-down
```{literalinclude} ../examples/tools/noise/peterson.py
:language: python
```
:::
