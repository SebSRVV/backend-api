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

    if not os.path.exists('criptos_predichas.json'):
        return jsonify({'error': 'Falta el archivo criptos_predichas.json'}), 500

    try:
        result = subprocess.run(
            ['python', 'modelo_portafolio.py', capital, riesgo, plazo],
            check=True,
            capture_output=True,
            text=True
        )

        data = json.loads(result.stdout)
        return jsonify({'recomendaciones': data})

    except subprocess.CalledProcessError as e:
        return jsonify({'error': f'Error ejecutando el script: {e.stderr}'}), 500
    except Exception as e:
        return jsonify({'error': f'Error inesperado: {str(e)}'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
