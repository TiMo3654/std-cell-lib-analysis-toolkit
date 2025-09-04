from .util import *

# Test vector generation for combinatorial cells

def generate_sensitive_vectors(expr):
    """
    Returns test vectors where flipping one input changes the output.
    """
    raw_expr = expr
    expr = preprocess_expression(expr)
    variables = extract_variables(raw_expr)
    n = len(variables)
    sensitive_vectors = []

    for bits in itertools.product([0, 1], repeat=n):
        input_vector = dict(zip(variables, bits))
        original_output = evaluate(expr, input_vector)

        for i in range(n):
            flipped_vector = input_vector.copy()
            flipped_vector[variables[i]] ^= 1
            flipped_output = evaluate(expr, flipped_vector)

            if flipped_output != original_output:
                sensitive_vectors.append((input_vector.copy(), variables[i]))

    return sensitive_vectors


def create_voltage_sources(testvector, v_high, v_low, tran_time):

    voltage_sources = []

    vector      = testvector[0]
    pulse_pin   = testvector[1]

    #slew_rate   = (0.8 * v_high - 0.2 * v_high) / tran_time # (V - V) / s

    # Pulse source

    if vector[pulse_pin] == 0: # input rising edge

        pulse_source = {
                        "node": pulse_pin,
                        "type": "pulse",
                        "val0": v_low,
                        "val1": v_high,
                        "rise": tran_time,
                        "fall": 1e-9,
                        "delay": 1e-9,
                        "width": 1
                    }
    else: # input falling edge

        pulse_source = {
                        "node": pulse_pin,
                        "type": "pulse",
                        "val0": v_high,
                        "val1": v_low,
                        "rise": 1e-9,
                        "fall": tran_time,
                        "delay": 1e-9,
                        "width": 1
                    }
        
    voltage_sources.append(pulse_source)

    # DC sources

    for pin, value in vector.items():

        if pin != pulse_pin:

            level = v_high if value == 1 else v_low

            source = {
                "node": pin,
                "type": "dc",
                "value": level
            }

            voltage_sources.append(source)


    # Supply voltage

    voltage_sources.append({"node": "vdd!", "type": "dc", "value": v_high})


    return voltage_sources


def generate_combinatorial_tb_netlist(pins, cell_name, voltage_sources, c_load, temperature, tran_time):
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
        'include "./../../data/xt018_subcircuits.scs"',
        ""
    ]

    body = [f"I3 ({' '.join(pins)}) {cell_name}"]

    for i, vs in enumerate(voltage_sources):

        source_type = vs["type"]


        if source_type == "dc":
            name    = f"V{i}"
            node    = vs["node"]
            value   = vs["value"]

            body.append(f"{name} ({node} 0) vsource dc={value} type=dc")

        elif source_type == "pulse":

            name    = f"V{i}"
            node    = vs["node"]

            val0    = vs["val0"]
            val1    = vs["val1"]
            delay   = vs["delay"]
            rise    = vs["rise"]
            fall    = vs["fall"]
            width   = vs["width"]

            body.append(
                f"{name} ({node} 0) vsource type=pulse val0={val0} val1={val1} "
                f"delay={delay} rise={rise} fall={fall} width={width}"
            )
        else:
            raise ValueError(f"Unknown source type: {source_type}")

    body.append(f"C0 (Q 0) capacitor c={c_load}")
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


def write_cell_testbench(cell : Group, v_sup : float, temperature : int, tran_time : float, path : str):

    q_pin       = select_pin(cell, "Q").attributes
    
    function    = attribute2dict(q_pin)['function'].strip('"')

    max_cap     = attribute2dict(q_pin)['max_capacitance'] * 1e-12 # pf

    max_tran    = attribute2dict(q_pin)['max_transition'] * 1e-9   # ns

    pins        = re.findall(r'[A-Z0-9]+', function)

    testvectors = generate_sensitive_vectors(function)

    netlist_id  = path + str(cell.args[0]) + "_"

    i = 0

    for vector in testvectors:

        voltage_sources = create_voltage_sources(vector, v_sup, 0.0, max_tran)

        netlist = generate_combinatorial_tb_netlist(  pins + ["Q", "0", "vdd!"] # add output and power pins
                                                    , str(cell.args[0])
                                                    , voltage_sources
                                                    , max_cap
                                                    , temperature
                                                    , tran_time) 

        with open(netlist_id + str(i) + ".scs", "w") as file:
            file.write(netlist)

        i += 1    