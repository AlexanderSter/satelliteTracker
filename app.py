import webbrowser
import skyfield_library as sfl
from flask import Flask, render_template, request, jsonify
from skyfield.api import load
import numpy as np

# declare globale Variable
satellites = None  
trackData = None
trackDataElevetion = None
location = None

app = Flask(__name__)


@app.route("/", methods=('GET', 'POST'))
def start_page():
    
    return render_template('index.html')

@app.route('/getSatData', methods=('GET', 'POST'))
def getSatData():
    global satellites
    data = request.get_json()
    satellites = sfl.importSatellitesFromCelestrak(str(data['value']))
    
    return satellites

@app.route('/getDescription', methods=('GET', 'POST'))
def getDescription():
    global satellites
    data = request.get_json()

    try:
        # Versuche, den Wert in Integer zu konvertieren
        key = int(data['value'])
        satDescription = sfl.importSatDataFromn2yo(satellites[key]['id'])


    except ValueError:
        return jsonify({'error': 'Invalid value. Please send a number.'}), 400

    # Ergebnis zurückgeben
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

    trackData = sfl.getTrackData(satelliteObject, location, time, elevation)
    trackDataElevetion = sfl.getTrackData_Elev(trackData, elevation)

    result = {'origin': trackData, 'elevation': trackDataElevetion}

    return jsonify(result)  

@app.route('/get_plotGroundTrack', methods=['GET', 'POST'])
def createPlotGroundTrack():
    
    global trackData
    global trackDataElevetion
    global location

    key = request.get_data()
    
    fig = sfl.createPlotGroundTrack(trackData[int(key)], trackDataElevetion[int(key)], location)

    return jsonify(fig.to_dict())

@app.route('/get_plotPolar', methods=['GET', 'POST'])
def createPlotPolar():
    
    global trackDataElevetion

    key = request.get_data()
    
    fig = sfl.createPlotPolar(trackDataElevetion[int(key)])

    return jsonify(fig.to_dict())

@app.route('/get_plotAltAzi', methods=['GET', 'POST'])
def createPlotAltAzi():
    
    global trackDataElevetion

    key = request.get_data()
    
    fig = sfl.createPlotAltAzi(trackDataElevetion[int(key)])

    return jsonify(fig.to_dict())

@app.route('/get_plotDistance', methods=['GET', 'POST'])
def createPlotDistance():
    
    global trackDataElevetion

    key = request.get_data()
    

    fig = sfl.createPlotDistance(trackDataElevetion[int(key)])

    return jsonify(fig.to_dict())


if __name__ == "__main__":
    webbrowser.open("http://127.0.0.1:5000")
    app.run(debug=True, use_reloader=False)