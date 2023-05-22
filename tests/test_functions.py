from __future__ import annotations
"""
Run tests for all functions defined in pysmo.sac.sacfunc
"""

from pysmo import (SAC, Station, Event, Seismogram, resample, detrend, envelope, gauss, plotseis,
                   distance, azimuth, backazimuth)
import matplotlib.pyplot as plt  # type: ignore
import os
import shutil
import pytest
import numpy as np
import matplotlib
matplotlib.use('Agg')


@pytest.fixture()
def sacfile() -> str:
    """Determine absolute path of the test SAC file."""
    return os.path.join(os.path.dirname(__file__), 'testfile.sac')


@pytest.fixture()
def data_objects(tmp_path_factory: pytest.TempPathFactory, sacfile: str) -> tuple[list[Seismogram], list[Station],
                                                                                  list[Event]]:
    """Returns instances of test objects to use with functions"""
    seismograms: list = []
    stations: list = []
    events: list = []
    # SAC provides seismogram, station and event
    test_sacfile = tmp_path_factory.mktemp("data") / "testfile.sac"
    shutil.copyfile(sacfile, test_sacfile)
    sacobj = SAC.from_file(str(test_sacfile))
    seismograms.append(sacobj)
    stations.append(sacobj)
    events.append(sacobj)
    return seismograms, stations, events


def test_resample(data_objects: tuple[list[Seismogram], ...]) -> None:
    """Resample Seismogram object and verify resampled data."""
    seismograms, *_ = data_objects
    for seis in seismograms:
        new_sampling_rate = seis.sampling_rate * 2
        resampled_seis = resample(seis, new_sampling_rate)
        assert pytest.approx(resampled_seis.sampling_rate) == seis.sampling_rate * 2
        assert pytest.approx(resampled_seis.data[6]) == 2202.0287804516634


def test_detrend(data_objects: tuple[list[Seismogram], ...]) -> None:
    """Detrend Seismogram object and verify mean is 0."""
    seismograms, *_ = data_objects
    for seis in seismograms:
        detrended_seis = detrend(seis)
        assert pytest.approx(np.mean(detrended_seis.data), abs=1e-6) == 0


@pytest.mark.mpl_image_compare(remove_text=True)
def test_plotseis(data_objects: tuple[list[Seismogram], ...]) -> plt.figure:
    seismograms, *_ = data_objects
    fig = plotseis(*seismograms, showfig=False, linewidth=0.5)  # type: ignore
    return fig


def test_envelope(data_objects: tuple[list[Seismogram], ...]) -> None:
    """
    Calculate gaussian envelope from Seismogram object and verify the calculated
    values. The reference values were obtained from previous runs of this function.
    """
    Tn = 50  # Center Gaussian filter at 50s period
    alpha = 50  # Set alpha (which determines filterwidth) to 50
    seismograms, *_ = data_objects
    for seis in seismograms:
        env_seis = envelope(seis, Tn, alpha)
        assert pytest.approx(env_seis.data[100]) == 6.109130497913114


def test_gauss(data_objects: tuple[list[Seismogram], ...]) -> None:
    """
    Calculate gaussian filtered data from SacFile object and verify the calculated
    values. The reference values were obtained from previous runs of this function.
    """
    Tn = 50  # Center Gaussian filter at 50s period
    alpha = 50  # Set alpha (which determines filterwidth) to 50
    seismograms, *_ = data_objects
    for seis in seismograms:
        gauss_seis = gauss(seis, Tn, alpha)
        assert pytest.approx(gauss_seis.data[100]) == -5.639860165811819


@pytest.mark.depends(on=['test_envelope', 'test_gauss'])
@pytest.mark.mpl_image_compare(remove_text=True)
def test_plot_gauss_env(data_objects: tuple[list[Seismogram], ...]) -> plt.figure:
    Tn = 50  # Center Gaussian filter at 50s period
    alpha = 50  # Set alpha (which determines filterwidth) to 50
    seismograms, *_ = data_objects
    seis, *_ = seismograms
    seis.data = seis.data - np.mean(seis.data)
    seis.label = "Unfiltered"  # type: ignore
    gauss_seis = gauss(seis, Tn, alpha)
    gauss_seis.label = "Gaussian filtered"  # type: ignore
    env_seis = envelope(seis, Tn, alpha)
    env_seis.label = "Envelope"  # type: ignore
    fig = plotseis(seis, gauss_seis, env_seis, showfig=False)  # type: ignore
    return fig


def test_azimuth(data_objects: tuple[list[Seismogram], list[Station], list[Event]]) -> None:
    """Calculate azimuth from Event and Station objects"""
    _, stations, events = data_objects
    for event, station in zip(events, stations):
        azimuth_wgs84 = azimuth(event, station)
        azimuth_clrk66 = azimuth(event, station, ellps='clrk66')
        assert pytest.approx(azimuth_wgs84) == 181.9199258637492
        assert pytest.approx(azimuth_clrk66) == 181.92001941872516


def test_backazimuth(data_objects: tuple[list[Seismogram], list[Station], list[Event]]) -> None:
    """Calculate backazimuth from Event and Station objects"""
    _, stations, events = data_objects
    for event, station in zip(events, stations):
        backazimuth_wgs84 = backazimuth(event, station)
        backazimuth_clrk66 = backazimuth(event, station, ellps='clrk66')
        assert pytest.approx(backazimuth_wgs84) == 2.4677533885335947
        assert pytest.approx(backazimuth_clrk66) == 2.467847115319614


def test_distance(data_objects: tuple[list[Seismogram], list[Station], list[Event]]) -> None:
    """Calculate distance from Event and Station objects"""
    _, stations, events = data_objects
    for event, station in zip(events, stations):
        distance_wgs84 = distance(event, station)
        distance_clrk66 = distance(event, station, ellps='clrk66')
        assert pytest.approx(distance_wgs84) == 1889154.9940066523
        assert pytest.approx(distance_clrk66) == 1889121.7781364019
