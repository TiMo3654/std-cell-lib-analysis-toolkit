from .util import *

def get_ff_pins(cell: Group) -> list:

    pins = []

    for pin in cell.get_groups('pin'):

        pins.append(pin.args[0])


    for bundle in cell.get_groups('bundle'):
                                
        pins = pins + [p.strip().strip("'") for p in attribute2dict(bundle.attributes)['members'][1:-1].split(",")]

    
    pins.sort() # Necessary for correct pin ordering in subcircuits
    
    return pins


def create_pulse( name
                , v_high
                , v_low
                , rise
                , fall
                , delay
                , width
                , period) -> dict:

    return {"node": name, "type": "pulse", "val0": v_low, "val1": v_high, "rise": rise,"fall": fall, "delay": delay, "width": width, "period": period}


def create_constant( name
                    , v_high
                    , v_low
                    , value) -> dict:
    
    level = v_high if value == 1 else v_low
    
    return {"node": name, "type": "dc", "value": level}


def create_ff_sources(  data_in
                      , pins
                      , v_high
                      , v_low
                      , data_rise
                      , data_fall
                      , data_delay
                      , data_width
                      , data_period
                      , clk_rise
                      , clk_fall
                      , clk_delay
                      , clk_width
                      , clk_period ) -> dict:
    
    sources = []
    
    constant_inputs = [p for p in pins if (p.startswith("D") and p != data_in)]

    scan_and_reset  = [p for p in pins if (p.startswith("R") or p.startswith("S"))]

    # Data In

    sources.append(create_pulse(data_in, v_high, v_low, data_rise, data_fall, data_delay, data_width, data_period))

    # Constant inputs

    for p in constant_inputs:

        sources.append(create_constant(p, v_high, v_low, 1))

    # Scan and reset

    for p in scan_and_reset:

        sources.append(create_constant(p, v_high, v_low, 1))
    
    # Clock

    sources.append(create_pulse("C", v_high, v_low, clk_rise, clk_fall, clk_delay, clk_width, clk_period))

    # Supply

    sources.append({"node": "vdd!", "type": "dc", "value": v_high})

    return sources   


def generate_ff_netlist(pins, cell_name, voltage_sources, c_load, temperature, tran_time):
    header = [
        "simulator lang=spectre",
        "global 0 vdd!",
        'include "/mnt/data/pdk/XKIT/xt018/cadence/v10_0/spectre/v10_0_4/lp5mos/config.scs" section=default',
        'include "/mnt/data/pdk/XKIT/xt018/cadence/v10_0/spectre/v10_0_4/lp5mos/param.scs" section=3s',
        'include "/mnt/data/pdk/XKIT/xt018/cadence/v10_0/spectre/v10_0_4/lp5mos/bip.scs" section=tm',
        'include "/mnt/data/pdk/XKIT/xt018/cadence/v10_0/spectre/v10_0_4/lp5mos/cap.scs" section=tm',
        'include "/mnt/data/pdk/XKIT/xt018/cadence/v10_0/spectre/v10_0_4/lp5mos/dio.scs" section=tm',
        'include "/mnt/data/pdk/XKIT/xt018/cadence/v10_0/spectre/v10_0_4/lp5mos/mos.scs" section=tm',
        'include "/mnt/data/pdk/XKIT/xt018/cadence/v10_0/spectre/v10_0_4/lp5mos/res.scs" section=tm',
        'include "./data/xt018_ff_subcircuits.scs"',
        ""
    ]

    # DUT

    body = [f"I0 ({' '.join(pins)}) {cell_name}"]

    # Input sources

    for i, vs in enumerate(voltage_sources):

        source_type = vs["type"]


        if source_type == "dc":

            body.append(f'V{i} ({vs["node"]} 0) vsource dc={vs["value"]} type=dc')

        elif source_type == "pulse":

            body.append(
                f'V{i} ({vs["node"]} 0) vsource type=pulse val0={vs["val0"]} val1={vs["val1"]} '
                f'delay={vs["delay"]} rise={vs["rise"]} fall={vs["fall"]} width={vs["width"]}, period={vs["period"]}'
            )
        else:
            raise ValueError(f"Unknown source type: {source_type}")
        
    # Output Loads

    outputs = [p for p in pins if p.startswith("Q")]

    for j, p in enumerate(outputs):

        body.append(f"C{j} ({p} 0) capacitor c={c_load}")

    body.append("")

    footer = [
        'simulatorOptions options psfversion="1.4.0" reltol=1e-3 vabstol=1e-6 \\',
        f'    iabstol=1e-12 temp={temperature} tnom=27 homotopy=all limit=delta scalem=1.0 \\',
        '    scale=1.0 compatible=spice2 gmin=1e-12 rforce=1 \\',
        '    redefinedparams=warning maxnotes=5 maxwarns=5 digits=5 cols=80 \\',
        '    pivrel=1e-3 sensfile="../psf/sens.output" checklimitdest=psf',
        f'tran tran stop={tran_time} errpreset=conservative write="spectre.ic" \\',
        '    writefinal="spectre.fc" annotate=status maxiters=5',
        'finalTimeOP info what=oppoint where=rawfile',
        'modelParameter info what=models where=rawfile',
        'element info what=inst where=rawfile',
        'outputParameter info what=output where=rawfile',
        'designParamVals info what=parameters where=rawfile',
        'primitives info what=primitives where=rawfile',
        'subckts info what=subckts where=rawfile',
        'saveOptions options save=allpub'
    ]

    return "\n".join(header + body + footer)