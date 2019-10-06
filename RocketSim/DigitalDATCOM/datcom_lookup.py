import subprocess
import numpy as np
import os

TEMPLATE_NAME = 'datcom_template.txt'
INPUT_NAME = 'current.dcm'
LOG_NAME = 'datcom_log.txt'
OUTPUT_NAME = 'datcom.out'
EXEC_NAME = 'datcom'
COLUMNS = ['ALPHA', 'CD', 'CL', 'CM', 'CN', 'CA', 'XCP',
           'CLA', 'CMA', 'CYB', 'CNB', 'CLB']
DATCOM_NUM_DECIMALS = 3


def parse_float(text):
    if '*' in text or 'NDM' in text:
        return text
    else:
        return float(text)

def lookup(machs, alphas, alts, cg, mass):
    # NOTE: There is a VERY insidious bug that occurs with
    # DATCOM: if you feed in too many decimal digits (~20)
    # it will throw a floating point exception of some kind
    # and truncate to an integer.
    machs = [round(mach, DATCOM_NUM_DECIMALS) for mach in machs]
    alphas = [round(alpha, DATCOM_NUM_DECIMALS) for alpha in alphas]
    alts = [round(alt, DATCOM_NUM_DECIMALS) for alt in alts]

    datcom_path = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(datcom_path, TEMPLATE_NAME), 'r') as f:
        datcom_input = f.read()

    replacements = {
        'INSERT_MACHS': ','.join([str(mach) for mach in machs]),
        'INSERT_NMACH': str(len(machs)),
        'INSERT_ALPHAS': ','.join([str(alpha) for alpha in alphas]),
        'INSERT_NALPHA': str(len(alphas)),
        'INSERT_ALTS': ','.join([str(alt) for alt in alts]),
        'INSERT_NALT': str(len(alts)),
        'INSERT_CG': str(cg),
        'INSERT_WEIGHT': str(mass)
    }

    for key, value in replacements.items():
        datcom_input = datcom_input.replace(key, value)

    with open(os.path.join(datcom_path, INPUT_NAME), 'w') as f:
        f.write(datcom_input)

    command = 'cd {}; echo {} | ./{}; cd ..'.format(
        datcom_path, INPUT_NAME, EXEC_NAME)
    with open(os.path.join(datcom_path, LOG_NAME), 'w') as f:
        subprocess.call(command, shell=True, stdout=f)

    with open(os.path.join(datcom_path, OUTPUT_NAME), 'r') as f:
        datcom_output = f.read()

    parameters = []
    coeffs = []

    while True:
        card_start = datcom_output.find('CHARACTERISTICS AT ANGLE OF ATTACK AND IN SIDESLIP')
        if card_start == -1:
            break
        conds_start = card_start + datcom_output[card_start:].find('\n0') + 3
        conds_end = conds_start + datcom_output[(conds_start + 1):].find('\n0')
        diffs_start = conds_end + datcom_output[(conds_end + 1):].find('\n0\n') + 4
        diffs_end = diffs_start + datcom_output[diffs_start:].find('\n0***')

        conds_text = datcom_output[conds_start:conds_end]
        diffs_text = datcom_output[diffs_start:diffs_end]

        # In some cases, DATCOM also generates output cards which
        # include basic flight data. We don't need that.
        if 'BASIC' not in conds_text:
            conds = [parse_float(cond) for cond in conds_text.split()]
            mach, alt = conds[:2]
            for diff_text in diffs_text.split('\n'):
                entries = [parse_float(diff) for diff in diff_text.split()]
                values = entries[1:]
                alpha = entries[0]
                parameters.append([mach, alpha, alt])
                coeffs.append(values)
        datcom_output = datcom_output[diffs_end:]

    return  np.array(parameters),np.array(coeffs)


# print(lookup([0.1, 0.2], [0.1, 0.2], [100, 200], 1, 1))
# print(lookup([0.1, 0.8, 0.9], [0.0], [0.0], 1, 1))
save_params, save_coeffs = lookup([0.1,0.2,0.3,0.4,0.5,0.6,1.4,1.5,1.6,1.7,1.8,1.9,2.0,2.5,3.0,3.5],[0.5,1.0,1.5,2.0,2.5,3.0,3.5,4.0,4.5,5.0],[26000,32526.32,39052.63,45578.95,52105.26,58631.58,65157.89,71684.21,78210.53,84736.84,91263.16,97789.47,104315.79,110842.11,117368.42,123894.74,130421.05],1.2,20)
np.savez('LookupTableParameters.npz',save_params)
np.savez('LookupTableCoeffs.npz',save_coeffs)
