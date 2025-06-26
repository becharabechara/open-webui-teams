from flask import Flask, render_template
from dotenv import load_dotenv
import os

app = Flask(__name__)

# Load environment variables
load_dotenv()

@app.route('/')
def index():
    debug_maintenance_status = os.getenv('DEBUG_MAINTENANCE_STATUS', 'True').lower() == 'true'
    return render_template('index.html', maintenance=debug_maintenance_status)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)