from skyfield.api import load, wgs84, EarthSatellite
from skyfield.iokit import parse_tle_file
import math
import re
import numpy as np
import plotly.graph_objects as go
import requests
from bs4 import BeautifulSoup

def importSatellitesFromCelestrak(group):
    # URL to fetch the JSON from
    url = f"https://celestrak.org/NORAD/elements/gp.php?GROUP={group}&FORMAT=tle"

    try:
        # Sending a GET request to the URL
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        # Get the content as a string
        content = response.text
        # Clean up
        content = content.strip()
        # Split the content into  array
        content = content.splitlines()

        satellites = {}
        key = 0

        for i, line in enumerate(content):
            if i % 3 == 0:  # Every 3rd line: Satellite name
                name = line.strip()
            elif i % 3 == 1:  # Every 3rd line + 1: Line 1
                line1 = line
                sat_id = line.split(' ')[1].replace('U', '')
            elif i % 3 == 2:  # Every 3rd line + 2: Line 2 and complete the entry
                line2 = line
                satellites[key] = {
                    'name': name,
                    'id': sat_id,
                    'object': [line1, line2]
                }
                key += 1


    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")

    
    return satellites

def importDescription(satelliteObject):
    line1 = satelliteObject[0]
    line2 = satelliteObject[1]
    satellite = EarthSatellite(line1, line2)

    intDesID = satellite.model.intldesg

    
    # URL to fetch
    url = f'https://nssdc.gsfc.nasa.gov/nmc/spacecraft/display.action?id=20{intDesID}'
    print(f'get description from: {url}')
    
    try:
        
        # Fetch the page
        response = requests.get(url)

        # Check if the request was successful
        if response.status_code == 200:
            html_content = response.text

            # Parse the HTML
            soup = BeautifulSoup(html_content, 'html.parser')

            # Extract sections
            facts_pattern = r'<h2>Facts in Brief</h2>\s*<p>(.*?)</p>'
            funding_agency_pattern = r'<h2>Funding Agency</h2>\s*<ul>(.*?)</ul>'
            discipline_pattern = r'<h2>Discipline</h2>\s*<ul>(.*?)</ul>'

            
            facts_section = re.search(facts_pattern, html_content, re.DOTALL).group(1).replace('\xa0', ' ')
            funding_agency_section = re.search(funding_agency_pattern, html_content, re.DOTALL).group(1).replace('\xa0', ' ')
            discipline_section = re.search(discipline_pattern, html_content, re.DOTALL).group(1).replace('\xa0', ' ')

            # Organize the data
            result = {
                'agency': re.findall(r'<li>(.*?)</li>', funding_agency_section),
                'discipline': re.findall(r'<li>(.*?)</li>', discipline_section),
                'launch_date': re.search(r'<strong>Launch\s*Date:</strong>\s*(.*?)<br/>', facts_section).group(1),
                'launch_site': re.search(r'<strong>Launch\s*Site:</strong>\s*(.*?)<br/>', facts_section).group(1),
                'launch_vehicle': re.search(r'<strong>Launch\s*Vehicle:</strong>\s*(.*?)<br/>', facts_section).group(1),
                'intDesID' : intDesID,
                'inclination' : np.rad2deg(satellite.model.inclo),
                'raan' : np.rad2deg(satellite.model.nodeo) ,
                'ecc' : satellite.model.ecco,
                'aop' : np.rad2deg(satellite.model.argpo),
                'meanano' : np.rad2deg(satellite.model.mo),
                'meanmot' : np.rad2deg(satellite.model.no_kozai),
                'description': soup.find('div', class_='urone').find('p').get_text(strip=True),
                'source': url

            }

            return result
        
        else:
            print(f"Failed to fetch the page: {response.status_code}")
            return {'source': url}
    except:
        print(f"Failed to fetch the page")
        return {'source': url}

def convertDateStringToArray(dateString):

    date_part, time_part = dateString.split("T")

    # Split further into components and convert to integers
    year, month, day = map(int, date_part.split("-"))
    hour, minute = map(int, time_part.split(":"))

    # Combine into a list
    datetime_array = [year, month, day, hour, minute]

    return np.array(datetime_array)

def getTrackData(satelliteObject, location, time, elevation):

    try:
        line1 = satelliteObject[0]
        line2 = satelliteObject[1]
        satellite = EarthSatellite(line1, line2)
        latitude, longitude = location[1], location[2]
        starttime, stoptime = time[0], time[1]

        ts = load.timescale()

        bluffton = wgs84.latlon(latitude, longitude)

        # for Satellite altitude, azimuth, and distance¶
        difference = satellite - bluffton

        # for 'rise', 'culminate', 'set'
        t0 = ts.utc(starttime[0], starttime[1], starttime[2], starttime[3], starttime[4])
        t1 = ts.utc(stoptime[0], stoptime[1], stoptime[2], stoptime[3], stoptime[4])

        data = {}
        t, events = satellite.find_events(bluffton, t0, t1, altitude_degrees=elevation)
        event_names = 'rise', 'culminate', 'set'
        i = 0
        value = []

        for ti, event in zip(t, events):
            name = event_names[event]
            value.append(ti.utc_strftime("%Y-%m-%dT%H:%M"))
            print(value)
            if name == 'set':
                data[i] = {
                    'rise': value[0], 
                    'culminate': value[1], 
                    'set': value[2]
                }
                i += 1
                value = []

        for i in range(len(data)):
            starttime = convertDateStringToArray(data[i]['rise'])
            stoptime = convertDateStringToArray(data[i]['set'])

            timeline = ts.utc(starttime[0], starttime[1], starttime[2], starttime[3], np.arange(0,100,1))
            data[i]['timeline'] = list(timeline.utc_strftime('%Y-%m-%dT%H:%M'))

            geocentric = satellite.at(timeline) 
            subpoint = geocentric.subpoint() # find sub sat point 
            
            lat, lon = wgs84.latlon_of(geocentric)

            data[i]['lat'] = list(lat.degrees)
            data[i]['lon'] = list(lon.degrees)

            topocentric = difference.at(timeline)
            alt, az, distance = topocentric.altaz()

            data[i]['alt'] = list(alt.degrees)
            data[i]['az'] = list(az.degrees)
            data[i]['distance'] = list(distance.km)

            pos = (satellite - bluffton).at(timeline)
            _, _, range_val, _, _, range_rate = pos.frame_latlon_and_rates(bluffton)
            
            data[i]['range'] = list(range_val.km)
            data[i]['range_rate'] = list(range_rate.km_per_s)
            
        return data
    
    except:
        
        return {'error': 'unable to create data'}

def getTrackData_Elev(trackData, elevation):
        
    data = {}
    for i in range(len(trackData)):
        row = trackData[i]
        timeline, lat, lon, alt, az, distance, range_rate = [],[],[],[],[],[],[] 
        for j in range(len(row['alt'])):
            
            if row['alt'][j] >= elevation:

                timeline.append(row['timeline'][j])
                lat.append(row['lat'][j])
                lon.append(row['lon'][j])
                alt.append(row['alt'][j])
                az.append(row['az'][j])
                distance.append(row['distance'][j])
                range_rate.append(row['range_rate'][j])
                
        
        if len(timeline) > 0:
            data[i] = {
                'timeline': timeline,
                'lat': lat,
                'lon': lon,
                'alt': alt,
                'az': az,
                'distance': distance,
                'range_rate': range_rate
            }
        
    return data

def createPlotGroundTrack(trackData, trackDataElevetion, location):
    latitude, longitude = location[1], location[2]

    # Create the map
    fig = go.Figure()

    # Add a scatter point for the location
    fig.add_trace(go.Scattergeo(
        lon=[longitude],
        lat=[latitude],
        mode='markers+text',
        text=[location[0]],
        textposition="top right",
        marker=dict(size=8, color="blue"),
        name="Location"
    ))

    # Add the ground track data
    fig.add_trace(go.Scattergeo(
        lon=trackData['lon'],
        lat=trackData['lat'],
        text=[timeline.replace('T', ' ') for timeline in trackData['timeline']],
        mode='lines+markers+text',
        line=dict(color="red"),
        textfont=dict(color="rgba(0, 0, 0, 0)"),
        marker=dict(size=4),
        name="Ground Track"
    ))

    # Add the ground track data for minimum elevation
    fig.add_trace(go.Scattergeo(
        lon=trackDataElevetion['lon'],
        lat=trackDataElevetion['lat'],
        text=[timeline.replace('T', ' ') for timeline in trackDataElevetion['timeline']],
        mode='lines+markers+text',
        line=dict(color="green"),
        textfont=dict(color="rgba(0, 0, 0, 0)"),
        marker=dict(size=4),
        name="Min Elevation Track"
    ))

    # Customize map appearance
    fig.update_geos(
        showcoastlines=True,
        coastlinecolor="Black",
        showland=True,
        landcolor="lightgray",
        showocean=True,
        oceancolor="lightblue",
        projection_type="natural earth"
    )

    # Add a title and layout
    fig.update_layout(
        title="Ground Track Visualization",
        geo=dict(
            showframe=False,
            showlakes=True,
            lakecolor="blue"
        ),
        margin={"r": 0, "t": 30, "l": 0, "b": 0}
    )

    return fig

def createPlotPolar(trackDataElevetion):
    fig = go.Figure()

    # Convert azimuth to radians and adjust altitude for polar representation
    theta = [az * np.pi / 180 for az in trackDataElevetion['az']]
    r = [90 - alt for alt in trackDataElevetion['alt']]

    fig.add_trace(go.Scatterpolar(
        r=r,
        theta=trackDataElevetion['az'],
        mode='lines+markers',
        name="Polar Track",
        marker=dict(color="green")
    ))

    fig.update_layout(
        polar=dict(
            angularaxis=dict(rotation=90),
            radialaxis=dict(range=[0, 90], tickvals=[30, 60, 90])
        ),
        title="Polar Plot (Altitude vs Azimuth)"
    )
    return fig

def createPlotAltAzi(trackDataElevetion):
    fig = go.Figure()

    # Plot Altitude
    fig.add_trace(go.Scatter(
        x=trackDataElevetion['timeline'],
        y=trackDataElevetion['alt'],
        mode='lines',
        name="Altitude",
        line=dict(color="blue")
    ))

   # Plot Azimuth
    fig.add_trace(go.Scatter(
        x=trackDataElevetion['timeline'],
        y=trackDataElevetion['az'],
        mode='lines',
        name="Azimuth",
        line=dict(color="red")
    ))

    # Update layout with correctly placed grid settings
    fig.update_layout(
        title="Altitude and Azimuth over Time",
        xaxis=dict(
            title="Date and Time",
            showgrid=True  # Enable gridlines for the x-axis
        ),
        yaxis=dict(
            title="Angles (°)",
            showgrid=True  # Enable gridlines for the y-axis
        ),
        legend=dict(
            title="Legend"
        )
    )

    return fig

def createPlotDistance(trackDataElevetion):
    fig = go.Figure()

    # Plot Distance
    fig.add_trace(go.Scatter(
        x=trackDataElevetion['timeline'],
        y=trackDataElevetion['distance'],
        mode='lines',
        name="Distance",
        line=dict(color="green")
    ))

    # Plot Speed
    fig.add_trace(go.Scatter(
        x=trackDataElevetion['timeline'],
        y=trackDataElevetion['range_rate'],  # Speed in km/s
        mode='lines',
        name="range’s rate of change",
        line=dict(color="blue"),
        yaxis="y2"  # Associate this trace with the second y-axis
    ))

    # Update layout for dual y-axes
    fig.update_layout(
        title="Distance and Rate of Change over Time",
        xaxis=dict(
            title="Date and Time",
            showgrid=True  # Enable gridlines for the x-axis
        ),
        yaxis=dict(
            title="Distance (km)",
            showgrid=True,  # Enable gridlines for the primary y-axis
            side="left"     # Place the primary y-axis on the left
        ),
        yaxis2=dict(
            title="rate of change (km/s)",
            overlaying="y",  # Overlay on the same plot
            side="right",    # Place the secondary y-axis on the right
            showgrid=False   # Optional: Disable gridlines for clarity
        ),
        legend=dict(
            title="Legend"
        )
    )

    return fig

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
