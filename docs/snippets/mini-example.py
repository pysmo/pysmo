from pysmo import MiniSeismogram
from pysmo.functions import clone_to_mini, copy_from_mini, resample
from pysmo.classes import SAC

# Read SAC file and clone it to a MiniSeismogram
sac = SAC.from_file("testfile.sac")
mini = clone_to_mini(MiniSeismogram, sac.seismogram)

# Process seismogram
resample(mini, mini.delta * 2)  # (1)!
...

# Copy processed seismogram back to the SAC file
copy_from_mini(mini, sac.seismogram)
sac.write("testfile_out.sac")
