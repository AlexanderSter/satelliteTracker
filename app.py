import webbrowser
import sc_pyLibrary as sc_lib
from flask import Flask, render_template, request, jsonify
from skyfield.api import load
import numpy as np

# declare globale Variable
satellites = None  
trackData = None
trackDataElevetion = None
location = None

app = Flask(__name__)


@app.route("/pageSatelliteTracker", methods=('GET', 'POST'))
def start_pageSatelliteTracker():
    
    return render_template('pageSatelliteTracker.html')

@app.route("/pageLinkBudget", methods=('GET', 'POST'))
def start_pageLinkBudget():
    
    return render_template('pageLinkBudget.html')

@app.route('/getSatData', methods=('GET', 'POST'))
def getSatData():
    global satellites
    data = request.get_json()
    satellites = sc_lib.importSatellitesFromCelestrak(str(data['value']))
    
    return satellites

@app.route('/getDescription', methods=('GET', 'POST'))
def getDescription():
    global satellites
    data = request.get_json()
    satelliteObject = satellites[data['key']]['object']
    
    try:
        # Versuche, den Wert in Integer zu konvertieren
        satDescription = sc_lib.importDescription(satelliteObject)


    except ValueError:
        return jsonify({'error': 'Invalid value. Please send a number.'}), 400

    return jsonify(satDescription)

@app.route('/getTrackData', methods=['GET', 'POST'])
def getTrackData():
    global satellites
    global trackData
    global trackDataElevetion
    global location

    data = request.get_json()
    satelliteObject = satellites[data['key']]['object']
    location = data['location']
    time = data['time']
    elevation = data['elevation']

    trackData = sc_lib.getTrackData(satelliteObject, location, time, elevation)
    trackDataElevetion = sc_lib.getTrackData_Elev(trackData, elevation)

    result = {'origin': trackData, 'elevation': trackDataElevetion}

    return jsonify(result)  

@app.route('/get_plotGroundTrack', methods=['GET', 'POST'])
def createPlotGroundTrack():
    
    global trackData
    global trackDataElevetion
    global location

    key = request.get_data()
    
    fig = sc_lib.createPlotGroundTrack(trackData[int(key)], trackDataElevetion[int(key)], location)

    return jsonify(fig.to_dict())

@app.route('/get_plotPolar', methods=['GET', 'POST'])
def createPlotPolar():
    
    global trackDataElevetion

    key = request.get_data()
    
    fig = sc_lib.createPlotPolar(trackDataElevetion[int(key)])

    return jsonify(fig.to_dict())

@app.route('/get_plotAltAzi', methods=['GET', 'POST'])
def createPlotAltAzi():
    
    global trackDataElevetion

    key = request.get_data()
    
    fig = sc_lib.createPlotAltAzi(trackDataElevetion[int(key)])

    return jsonify(fig.to_dict())

@app.route('/get_plotDistance', methods=['GET', 'POST'])
def createPlotDistance():
    
    global trackDataElevetion

    key = request.get_data()
    

    fig = sc_lib.createPlotDistance(trackDataElevetion[int(key)])

    return jsonify(fig.to_dict())

@app.route('/getLinkBudget', methods=['GET', 'POST'])
def getlinkBudget():
    data = request.get_json()
    linkBudgetData = sc_lib.getLinkBudget(data['bandwidth'], data['eirp'], data['distance'], data['frequency'], data['antennaGainRx'], data['receiverGain'], data['bitrate'], data['bitsPerSymbol'], data['rollOffFactor'], data['noiseFigure'], data['txPower'], data['noiseTempAn'])
    return jsonify(linkBudgetData)

if __name__ == "__main__":
    webbrowser.open("http://127.0.0.1:5000/pageSatelliteTracker")
    app.run(debug=False, use_reloader=False)