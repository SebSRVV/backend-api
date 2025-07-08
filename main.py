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
        # Ejecutar el script con argumentos
        result = subprocess.run(
            ['python', 'modelo_portafolio.py', capital, riesgo, plazo],
            check=True,
            capture_output=True,
            text=True
        )

        # Verificar que se generó el archivo de salida
        if not os.path.exists('recomendaciones.json'):
            return jsonify({'error': 'No se generó el archivo recomendaciones.json'}), 500

        # Leer y devolver el contenido del archivo JSON
        with open('recomendaciones.json', 'r') as f:
            data = json.load(f)

        return jsonify({'recomendaciones': data})

    except subprocess.CalledProcessError as e:
        return jsonify({'error': f'Error al ejecutar el script: {e.stderr}'}), 500
    except Exception as e:
        return jsonify({'error': f'Error inesperado: {str(e)}'}), 500

# Ejecutar con puerto dinámico para Railway
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
