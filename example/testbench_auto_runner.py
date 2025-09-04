import pyspectre.functional as ps
import os

# Run this script from a terminal where the "spectre" command is available

netlist  = './netlists/tb_INHDX0_0.scs'
includes = []

# Start Interactive session
session  = ps.start_session(netlist, includes)

# Simulate
results  = ps.run_all(session)

# End Interactive session
ps.stop_session(session)

results["Transient Analysis `tran': time = (0 s -> 12 ns)"].to_pickle("./results/sim_INHDX0_0.pkl")

# Clean

os.remove("spectre.ic")
os.remove("spectre.fc")