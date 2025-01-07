def getLinkBudget(bandwidth, eirp, distance, frequency, antennaGainRx_dB, receiverGain_dB, bitrate, bitsPerSymbol, rollOffFactor, noiseFigure_dB, txPower, noiseTempAn):

    antennaGainRx = 10**(antennaGainRx_dB/10)
    receiverGain = 10**(receiverGain_dB/10)
    noiseFigure = 10**(noiseFigure_dB/10)

    k = 1.38e-23
    temp_0 = 290
    wavelength = 3e8 / frequency

    antennaGainTx = eirp / txPower
    antennaGainTx_dB = 10*np.log10(antennaGainTx)
    pathloss = ((4 * np.pi * distance) / wavelength)**2
    pathloss_dB =  10*np.log10(pathloss)
    powerFluxDensity = eirp / (4 * np.pi * distance**2)

    noiseTempEq = (noiseFigure - 1) * temp_0
    noiseOut = k * receiverGain * (noiseTempAn + noiseTempEq) * bandwidth
    noiseOut_dB = 10*np.log10(noiseOut)
    noiseIn = k * noiseTempAn * bandwidth
    noiseIn_dB = 10*np.log10(noiseIn)

    signalIn = antennaGainTx * txPower * antennaGainRx * 1/pathloss
    signalIn_dB = 10*np.log10(signalIn)

    signalOut = signalIn * receiverGain
    signalOut_dB = 10*np.log10(signalOut)

    snrIn = signalIn / noiseIn
    snrIn_dB =  10*np.log10(snrIn)
    snrOut = signalOut / noiseOut
    snrOut_dB =  10*np.log10(snrOut)
    
    # Wert zu hoch -> logarithmisch anderer Wert
    attentuation = txPower / signalIn

    antennaEffectiveArea = antennaGainRx * wavelength**2 / (4*np.pi)
    antennaEfficiency = 0.6
    antennaArea = antennaEffectiveArea / antennaEfficiency
    antennaDiameter = 2* np.sqrt(antennaArea/np.pi)

    M = 2**bitsPerSymbol

    symbolRate = bitrate/bitsPerSymbol
    spectralEfficiency = np.log2(M)/(1+rollOffFactor)

    requiredBandwidth = bitrate / spectralEfficiency

    energyPerBit = snrOut * requiredBandwidth / bitrate

    bitErrorRatio = 1/2 * math.erfc(np.sqrt(energyPerBit))

    txPower_dB = 10*np.log10(txPower)
    eirp_dB = 10*np.log10(eirp)
    bandwidth_dB = 10*np.log10(bandwidth)

    govert_dB = 10*np.log10(antennaGainRx / (noiseTempAn+noiseTempEq))

    result = {
        'frequency': {'value': frequency, 'dB': "", 'unit': ["Hz", ""]},
        'wavelength': {'value': wavelength, 'dB': "", 'unit': ["m",""]},
        'bandwidth': {'value': bandwidth, 'dB': bandwidth_dB, 'unit': ["Hz", "dB"]},
        'txPower': {'value': txPower, 'dB': txPower_dB, 'unit': ["W", "dBW"]},
        'antennaGainTx': {'value': antennaGainTx, 'dB': antennaGainTx_dB, 'unit': ["", "dBi"]},
        'eirp': {'value': eirp, 'dB': eirp_dB, 'unit': ["W", "dBW"]},
        'distance': {'value': distance, 'dB': "", 'unit': ["m", ""]},
        'pathloss': {'value': pathloss, 'dB': pathloss_dB, 'unit': ["", "dB"]},
        'powerFluxDensity': {'value': powerFluxDensity, 'dB': "", 'unit': ["W/m²", ""]},
        'antennaDiameter': {'value': antennaDiameter, 'dB': "", 'unit': ["m", ""]},
        'antennaArea': {'value': antennaArea, 'dB': "", 'unit': ["m²", ""]},
        'antennaEffectiveArea': {'value': antennaEffectiveArea, 'dB': "", 'unit': ["m²", ""]},
        'antennaEfficiency': {'value': antennaEfficiency * 100, 'dB': "", 'unit': ["%", ""]},
        'antennaGainRx': {'value': antennaGainRx, 'dB': antennaGainRx_dB, 'unit': ["", "dBi"]},
        'signalIn': {'value': signalIn, 'dB': signalIn_dB, 'unit': ["W", "dBW"]},
        'receiverGain': {'value': receiverGain, 'dB': receiverGain_dB, 'unit': ["", "dB"]},
        'signalOut': {'value': signalOut, 'dB': signalOut_dB, 'unit': ["W", "dBW"]},
        'noiseTempAn': {'value': noiseTempAn, 'dB': "", 'unit': ["K", ""]},
        'noiseIn': {'value': noiseIn, 'dB': noiseIn_dB, 'unit': ["W", "dBW"]},
        'snrIn': {'value': snrIn, 'dB': snrIn_dB, 'unit': ["", "dB"]},
        'noiseFigure': {'value': noiseFigure, 'dB': noiseFigure_dB, 'unit': ["", "dB"]},
        'noiseTempEq': {'value': noiseTempEq, 'dB': "", 'unit': ["K", ""]},
        'noiseOut': {'value': noiseOut, 'dB': noiseOut_dB, 'unit': ["W", "dBW"]},
        'snrOut': {'value': snrOut, 'dB': snrOut_dB, 'unit': ["", "dB"]},
        'bitsPerSymbol': {'value': bitsPerSymbol, 'dB': "", 'unit': ["", ""]},
        'bitrate': {'value': bitrate, 'dB': "", 'unit': ["bits/s", ""]},
        'symbolRate': {'value': symbolRate, 'dB': "", 'unit': ["Sym/s", ""]},
        'rollOffFactor': {'value': rollOffFactor, 'dB': "", 'unit': ["", ""]},
        'requiredBandwidth': {'value': requiredBandwidth, 'dB': "", 'unit': ["Hz", ""]},
        'energyPerBit': {'value': energyPerBit, 'dB': "", 'unit': ["", ""]},
        'bitErrorRatio': {'value': bitErrorRatio, 'dB': "", 'unit': ["", ""]},
        'govert': {'value': "", 'dB': govert_dB, 'unit': ["", "dB/K"]}
    }

    return result
