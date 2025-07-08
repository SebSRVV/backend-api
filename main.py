from flask import Flask, request, jsonify
import subprocess
import os
import json

app = Flask(__name__)

@app.route('/recomendar', methods=['GET'])
def recomendar():
    capital = request.args.get('capital')
    riesgo = request.args.get('riesgo')
    plazo = request.args.get('plazo')

    if not capital or not riesgo or not plazo:
        return jsonify({'error': 'Faltan parámetros'}), 400

    try:
        result = subprocess.run(
            ['python', 'modelo_portafolio.py', capital, riesgo, plazo],
            check=True,
            capture_output=True,
            text=True
        )

        # Se espera que el script genere un JSON en un archivo
        if not os.path.exists('recomendaciones.json'):
            return jsonify({'error': 'No se generó el archivo'}), 500

        with open('recomendaciones.json', 'r') as f:
            data = json.load(f)

        return jsonify(data)

    except subprocess.CalledProcessError as e:
        return jsonify({'error': str(e.stderr)}), 500
