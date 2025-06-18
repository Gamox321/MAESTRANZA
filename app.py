from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_aqui'

# Configuración de la base de datos
DATABASE = 'inventario.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Inicializa la base de datos con las tablas necesarias"""
    conn = get_db_connection()
    
    # Tabla de usuarios
    conn.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            rol TEXT NOT NULL,
            nombre TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabla de piezas/componentes
    conn.execute('''
        CREATE TABLE IF NOT EXISTS piezas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descripcion TEXT NOT NULL,
            numero_serie TEXT UNIQUE NOT NULL,
            ubicacion_fisica TEXT NOT NULL,
            stock_actual INTEGER DEFAULT 0,
            stock_minimo INTEGER DEFAULT 5,
            precio REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabla de movimientos (trazabilidad)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS movimientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pieza_id INTEGER NOT NULL,
            tipo_movimiento TEXT NOT NULL,
            cantidad INTEGER NOT NULL,
            usuario_id INTEGER NOT NULL,
            observaciones TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (pieza_id) REFERENCES piezas (id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
    ''')
    
    # Tabla de kits
    conn.execute('''
        CREATE TABLE IF NOT EXISTS kits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            descripcion TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabla de componentes de kits
    conn.execute('''
        CREATE TABLE IF NOT EXISTS kit_componentes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kit_id INTEGER NOT NULL,
            pieza_id INTEGER NOT NULL,
            cantidad_requerida INTEGER NOT NULL,
            FOREIGN KEY (kit_id) REFERENCES kits (id),
            FOREIGN KEY (pieza_id) REFERENCES piezas (id)
        )
    ''')
    
    # Tabla de alertas
    conn.execute('''
        CREATE TABLE IF NOT EXISTS alertas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pieza_id INTEGER NOT NULL,
            tipo_alerta TEXT NOT NULL,
            mensaje TEXT NOT NULL,
            estado TEXT DEFAULT 'activa',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (pieza_id) REFERENCES piezas (id)
        )
    ''')
    
    # Insertar datos de ejemplo
    # Usuario administrador por defecto
    admin_password = generate_password_hash('admin123')
    conn.execute('''
        INSERT OR IGNORE INTO usuarios (username, password, rol, nombre) 
        VALUES (?, ?, ?, ?)
    ''', ('admin', admin_password, 'Administrador', 'Administrador del Sistema'))
    
    # Usuarios de ejemplo
    gestor_password = generate_password_hash('gestor123')
    conn.execute('''
        INSERT OR IGNORE INTO usuarios (username, password, rol, nombre) 
        VALUES (?, ?, ?, ?)
    ''', ('gestor', gestor_password, 'Gestor', 'Gestor de Inventario'))
    
    logistica_password = generate_password_hash('logistica123')
    conn.execute('''
        INSERT OR IGNORE INTO usuarios (username, password, rol, nombre) 
        VALUES (?, ?, ?, ?)
    ''', ('logistica', logistica_password, 'Logística', 'Encargado de Logística'))
    
    # Piezas de ejemplo
    piezas_ejemplo = [
        ('Tornillo M8x20', 'T001', 'Estante A1', 50, 10, 0.15),
        ('Tuerca M8', 'N001', 'Estante A2', 3, 15, 0.08),
        ('Arandela plana 8mm', 'W001', 'Estante A3', 25, 20, 0.05),
        ('Bearing 6205', 'B001', 'Estante B1', 8, 5, 12.50),
        ('Motor 220V 1HP', 'M001', 'Almacén C', 2, 3, 450.00)
    ]
    
    for pieza in piezas_ejemplo:
        conn.execute('''
            INSERT OR IGNORE INTO piezas (descripcion, numero_serie, ubicacion_fisica, stock_actual, stock_minimo, precio) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', pieza)
    
    conn.commit()
    conn.close()

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute(
            'SELECT * FROM usuarios WHERE username = ?', (username,)
        ).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['rol'] = user['rol']
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Credenciales inválidas')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# CRUD Piezas
@app.route('/piezas')
def piezas():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    piezas = conn.execute('SELECT * FROM piezas ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('piezas.html', piezas=piezas)

@app.route('/api/piezas', methods=['GET', 'POST'])
def api_piezas():
    if 'user_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    
    conn = get_db_connection()
    
    if request.method == 'POST':
        data = request.get_json()
        conn.execute('''
            INSERT INTO piezas (descripcion, numero_serie, ubicacion_fisica, stock_actual, stock_minimo, precio)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (data['descripcion'], data['numero_serie'], data['ubicacion_fisica'], 
              data['stock_actual'], data['stock_minimo'], data['precio']))
        conn.commit()
        
        # Verificar si necesita alerta
        if data['stock_actual'] <= data['stock_minimo']:
            conn.execute('''
                INSERT INTO alertas (pieza_id, tipo_alerta, mensaje)
                VALUES (?, ?, ?)
            ''', (conn.lastrowid, 'stock_minimo', f'Stock bajo: {data["descripcion"]}'))
            conn.commit()
        
        conn.close()
        return jsonify({'success': True})
    
    piezas = conn.execute('SELECT * FROM piezas ORDER BY id DESC').fetchall()
    conn.close()
    return jsonify([dict(pieza) for pieza in piezas])

@app.route('/api/piezas/<int:pieza_id>', methods=['PUT', 'DELETE'])
def api_pieza_detail(pieza_id):
    if 'user_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    
    conn = get_db_connection()
    
    if request.method == 'PUT':
        data = request.get_json()
        conn.execute('''
            UPDATE piezas 
            SET descripcion=?, numero_serie=?, ubicacion_fisica=?, stock_actual=?, stock_minimo=?, precio=?
            WHERE id=?
        ''', (data['descripcion'], data['numero_serie'], data['ubicacion_fisica'], 
              data['stock_actual'], data['stock_minimo'], data['precio'], pieza_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    elif request.method == 'DELETE':
        conn.execute('DELETE FROM piezas WHERE id=?', (pieza_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})

# Movimientos (Trazabilidad)
@app.route('/movimientos')
def movimientos():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    movimientos = conn.execute('''
        SELECT m.*, p.descripcion as pieza_desc, u.nombre as usuario_nombre
        FROM movimientos m
        JOIN piezas p ON m.pieza_id = p.id
        JOIN usuarios u ON m.usuario_id = u.id
        ORDER BY m.created_at DESC
    ''').fetchall()
    conn.close()
    return render_template('movimientos.html', movimientos=movimientos)

@app.route('/api/movimientos', methods=['POST'])
def api_movimientos():
    if 'user_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    
    data = request.get_json()
    conn = get_db_connection()
    
    # Registrar movimiento
    conn.execute('''
        INSERT INTO movimientos (pieza_id, tipo_movimiento, cantidad, usuario_id, observaciones)
        VALUES (?, ?, ?, ?, ?)
    ''', (data['pieza_id'], data['tipo_movimiento'], data['cantidad'], 
          session['user_id'], data.get('observaciones', '')))
    
    # Actualizar stock
    if data['tipo_movimiento'] == 'entrada':
        conn.execute('UPDATE piezas SET stock_actual = stock_actual + ? WHERE id = ?', 
                    (data['cantidad'], data['pieza_id']))
    elif data['tipo_movimiento'] == 'salida':
        conn.execute('UPDATE piezas SET stock_actual = stock_actual - ? WHERE id = ?', 
                    (data['cantidad'], data['pieza_id']))
    
    # Verificar alertas
    pieza = conn.execute('SELECT * FROM piezas WHERE id = ?', (data['pieza_id'],)).fetchone()
    if pieza['stock_actual'] <= pieza['stock_minimo']:
        conn.execute('''
            INSERT INTO alertas (pieza_id, tipo_alerta, mensaje)
            VALUES (?, ?, ?)
        ''', (data['pieza_id'], 'stock_minimo', f'Stock bajo: {pieza["descripcion"]}'))
    
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# Kits
@app.route('/kits')
def kits():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    kits = conn.execute('SELECT * FROM kits ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('kits.html', kits=kits)

@app.route('/api/kits', methods=['GET', 'POST'])
def api_kits():
    if 'user_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    
    conn = get_db_connection()
    
    if request.method == 'POST':
        data = request.get_json()
        conn.execute('INSERT INTO kits (nombre, descripcion) VALUES (?, ?)', 
                    (data['nombre'], data['descripcion']))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    kits = conn.execute('SELECT * FROM kits ORDER BY id DESC').fetchall()
    conn.close()
    return jsonify([dict(kit) for kit in kits])

# Alertas
@app.route('/alertas')
def alertas():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    alertas = conn.execute('''
        SELECT a.*, p.descripcion as pieza_desc, p.stock_actual, p.stock_minimo
        FROM alertas a
        JOIN piezas p ON a.pieza_id = p.id
        WHERE a.estado = 'activa'
        ORDER BY a.created_at DESC
    ''').fetchall()
    conn.close()
    return render_template('alertas.html', alertas=alertas)

@app.route('/api/alertas/<int:alerta_id>/resolver', methods=['POST'])
def resolver_alerta(alerta_id):
    if 'user_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    
    conn = get_db_connection()
    conn.execute('UPDATE alertas SET estado = ? WHERE id = ?', ('resuelta', alerta_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# Usuarios (solo para administradores)
@app.route('/usuarios')
def usuarios():
    if 'user_id' not in session or session.get('rol') != 'Administrador':
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    usuarios = conn.execute('SELECT id, username, rol, nombre, created_at FROM usuarios ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('usuarios.html', usuarios=usuarios)

if __name__ == '__main__':
    init_db()
    app.run(debug=True) 