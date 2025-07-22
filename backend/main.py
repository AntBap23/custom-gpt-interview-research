from flask import Flask
from routes.simulate import simulate_bp
from routes.compare import compare_bp
from routes.gioia import gioia_bp
from routes.framework import framework_bp
from routes.export import export_bp
from routes.auth import auth_bp
from routes.payments import payments_bp
import os

app = Flask(__name__)

# Ensure outputs directory exists
os.makedirs('outputs', exist_ok=True)

# Register blueprints
app.register_blueprint(simulate_bp)
app.register_blueprint(compare_bp)
app.register_blueprint(gioia_bp)
app.register_blueprint(framework_bp)
app.register_blueprint(export_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(payments_bp)

if __name__ == '__main__':
    app.run(debug=True) 