from skyfield.api import load, wgs84, EarthSatellite
from skyfield.iokit import parse_tle_file
from playwright.sync_api import sync_playwright
import re
import numpy as np
import plotly.graph_objects as go
import requests

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

def importSatDataFromn2yo(satID):
    url = 'https://www.n2yo.com/satellite/?s='
    # url = url + str(satID)
    url = url + str(satID) if isinstance(satID, (int, str)) else ''

    if (len(url) != 0):
        with sync_playwright() as p:
            # Launch the browser (you can use Chromium, Firefox, or WebKit)
            browser = p.chromium.launch(headless=True)  # headless=True means no UI
            page = browser.new_page()

            # Open the target URL
            page.goto(url)

            # Wait for the content to load (you can wait for specific elements to appear)
            page.wait_for_selector('#satinfo')

            # Extract the content inside the div with id 'satinfo'
            satinfo_content = page.inner_text('#satinfo')

            # Close the browser
            browser.close()

        satinfo_content = satinfo_content.split('\n')

        # Define regex patterns
        patterns = {
            'perigee': r'Perigee:\s*([\d.]+ km)',
            'apogee': r'Apogee:\s*([\d.]+ km)',
            'inclination': r'Inclination:\s*([\d.]+ °)',
            'period': r'Period:\s*([\d.]+ minutes)',
            'semi_major_axis': r'Semi major axis:\s*([\d.]+ km)',
            'rcs': r'RCS:\s*([\d.]+ m2 \(.*\))',
            'launch_date': r'Launch date:\s*(.+)',
            'source': r'Source:\s*(.+)',
            'launch_site': r'Launch site:\s*(.+)',
        }

        # Initialize result dictionary
        result = {key: None for key in patterns}


        # Extract values using regex
        for line in satinfo_content:
            for key, pattern in patterns.items():
                if not result[key]:  # Avoid overwriting if already matched
                    match = re.search(pattern, line)
                    if match:
                        result[key] = match.group(1)


        patterns = {
            'uplink': r'Uplink \(MHz\):\s*([\d.\-]+)',
            'downlink': r'Downlink \(MHz\):\s*([\d.\-]+)',
            'beacon': r'Beacon \(MHz\):\s*([\d.\-]+)',
            'mode': r'Mode:\s*(.+)',
            'call_sign': r'Call sign:\s*(.*)',
            'status': r'Status:\s*(.+)'
        }

        currentRadio = {key: None for key in patterns}
        radioData = []

        for line in satinfo_content:
            for key, pattern in patterns.items():
                if not currentRadio[key]:  # Avoid overwriting if already matched
                    match = re.search(pattern, line)
                    if match:
                        currentRadio[key] = match.group(1).strip()

                        if key == 'status':
                            radioData.append(currentRadio)
                            currentRadio = {key: None for key in patterns}

        # Result
        result['radio'] = {i: radio for i, radio in enumerate(radioData)}
        result['description'] = satinfo_content[-1]
        return result

def convertDateStringToArray(dateString):

    date_part, time_part = dateString.split("T")

    # Split further into components and convert to integers
    year, month, day = map(int, date_part.split("-"))
    hour, minute = map(int, time_part.split(":"))

    # Combine into a list
    datetime_array = [year, month, day, hour, minute]

    return np.array(datetime_array)

def getTrackData(satelliteObject, location, time, elevation):

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

