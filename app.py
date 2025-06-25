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
    
    # Tabla de lotes
    conn.execute('''
        CREATE TABLE IF NOT EXISTS lotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pieza_id INTEGER NOT NULL,
            numero_lote TEXT NOT NULL,
            fecha_fabricacion DATE,
            fecha_vencimiento DATE NOT NULL,
            cantidad_inicial INTEGER NOT NULL,
            cantidad_actual INTEGER NOT NULL,
            proveedor TEXT,
            estado TEXT DEFAULT 'activo',
            observaciones TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (pieza_id) REFERENCES piezas (id)
        )
    ''')
    
    # Tabla de movimientos de lotes
    conn.execute('''
        CREATE TABLE IF NOT EXISTS movimientos_lotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lote_id INTEGER NOT NULL,
            tipo_movimiento TEXT NOT NULL,
            cantidad INTEGER NOT NULL,
            usuario_id INTEGER NOT NULL,
            observaciones TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lote_id) REFERENCES lotes (id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
    ''')
    
    # Tabla de alertas
    conn.execute('''
        CREATE TABLE IF NOT EXISTS alertas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pieza_id INTEGER,
            lote_id INTEGER,
            tipo_alerta TEXT NOT NULL,
            mensaje TEXT NOT NULL,
            estado TEXT DEFAULT 'activa',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (pieza_id) REFERENCES piezas (id),
            FOREIGN KEY (lote_id) REFERENCES lotes (id)
        )
    ''')
    
    # Tabla de historial de precios (U003)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS historial_precios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pieza_id INTEGER NOT NULL,
            precio_anterior REAL,
            precio_nuevo REAL NOT NULL,
            proveedor TEXT,
            usuario_id INTEGER NOT NULL,
            motivo TEXT,
            observaciones TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (pieza_id) REFERENCES piezas (id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
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
    
    # Datos de ejemplo para historial de precios
    historial_ejemplo = [
        # Tornillo M8x20 (id=1)
        (1, None, 0.15, 1, 'Precio inicial', 'Tornillos SA', '2024-01-15 10:00:00'),
        (1, 0.15, 0.18, 1, 'Aumento proveedor', 'Tornillos SA', '2024-02-10 14:30:00'),
        (1, 0.18, 0.16, 1, 'Negociación de precio', 'Metales Ltda', '2024-03-05 09:15:00'),
        
        # Tuerca M8 (id=2)
        (2, None, 0.08, 1, 'Precio inicial', 'Ferretería Central', '2024-01-15 10:05:00'),
        (2, 0.08, 0.09, 1, 'Inflación', 'Ferretería Central', '2024-02-20 16:45:00'),
        
        # Bearing 6205 (id=4)
        (4, None, 12.50, 1, 'Precio inicial', 'Bearings Corp', '2024-01-15 10:15:00'),
        (4, 12.50, 14.00, 1, 'Cambio de proveedor', 'Rodamientos Express', '2024-02-15 11:00:00'),
        (4, 14.00, 13.20, 1, 'Descuento por volumen', 'Rodamientos Express', '2024-03-20 13:30:00'),
        
        # Motor 220V 1HP (id=5)
        (5, None, 450.00, 1, 'Precio inicial', 'Motores Eléctricos SA', '2024-01-15 10:20:00'),
        (5, 450.00, 485.00, 1, 'Aumento materia prima', 'Motores Eléctricos SA', '2024-02-25 15:00:00'),
    ]
    
    for historial in historial_ejemplo:
        conn.execute('''
            INSERT OR IGNORE INTO historial_precios 
            (pieza_id, precio_anterior, precio_nuevo, usuario_id, motivo, proveedor, created_at) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', historial)
    
    # Datos de ejemplo para movimientos
    movimientos_ejemplo = [
        # Entradas recientes
        (1, 'entrada', 100, 1, 'Compra mensual de tornillos', '2024-12-01 08:30:00'),
        (2, 'entrada', 200, 1, 'Reposición de stock', '2024-12-01 09:15:00'),
        (4, 'entrada', 20, 2, 'Pedido especial bearings', '2024-12-02 10:00:00'),
        (5, 'entrada', 5, 2, 'Motores nuevos', '2024-12-02 11:30:00'),
        
        # Salidas de producción
        (1, 'salida', 50, 3, 'Proyecto línea A', '2024-12-03 14:20:00'),
        (2, 'salida', 50, 3, 'Proyecto línea A', '2024-12-03 14:25:00'),
        (3, 'salida', 30, 3, 'Mantenimiento preventivo', '2024-12-04 08:45:00'),
        (4, 'salida', 3, 2, 'Reparación urgente', '2024-12-04 16:30:00'),
        
        # Movimientos del mes anterior
        (1, 'entrada', 75, 1, 'Reposición automática', '2024-11-15 09:00:00'),
        (1, 'salida', 80, 3, 'Proyecto línea B', '2024-11-20 13:15:00'),
        (2, 'entrada', 150, 1, 'Compra trimestral', '2024-11-10 10:30:00'),
        (2, 'salida', 120, 3, 'Múltiples proyectos', '2024-11-25 15:45:00'),
        (5, 'salida', 1, 2, 'Instalación nueva', '2024-11-28 11:00:00'),
        
        # Movimientos más antiguos
        (3, 'entrada', 100, 1, 'Stock inicial', '2024-10-01 08:00:00'),
        (3, 'salida', 75, 3, 'Mantenimiento mayor', '2024-10-15 14:30:00'),
        (4, 'entrada', 15, 1, 'Pedido regular', '2024-10-20 09:30:00'),
        (4, 'salida', 7, 2, 'Servicio técnico', '2024-10-25 16:15:00'),
    ]
    
    for movimiento in movimientos_ejemplo:
        conn.execute('''
            INSERT OR IGNORE INTO movimientos 
            (pieza_id, tipo_movimiento, cantidad, usuario_id, observaciones, created_at) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', movimiento)
    
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
        
        # Crear pieza
        cursor = conn.execute('''
            INSERT INTO piezas (descripcion, numero_serie, ubicacion_fisica, stock_actual, stock_minimo, precio)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (data['descripcion'], data['numero_serie'], data['ubicacion_fisica'], 
              data['stock_actual'], data['stock_minimo'], data['precio']))
        
        pieza_id = cursor.lastrowid
        
        # Registrar precio inicial en historial
        conn.execute('''
            INSERT INTO historial_precios (pieza_id, precio_anterior, precio_nuevo, usuario_id, motivo, proveedor)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (pieza_id, None, data['precio'], session['user_id'], 'Precio inicial', 
              data.get('proveedor', '')))
        
        # Verificar si necesita alerta
        if data['stock_actual'] <= data['stock_minimo']:
            conn.execute('''
                INSERT INTO alertas (pieza_id, tipo_alerta, mensaje)
                VALUES (?, ?, ?)
            ''', (pieza_id, 'stock_minimo', f'Stock bajo: {data["descripcion"]}'))
        
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
        
        # Obtener precio anterior para el historial
        pieza_actual = conn.execute('SELECT precio FROM piezas WHERE id=?', (pieza_id,)).fetchone()
        precio_anterior = pieza_actual['precio'] if pieza_actual else None
        precio_nuevo = data['precio']
        
        # Actualizar pieza
        conn.execute('''
            UPDATE piezas 
            SET descripcion=?, numero_serie=?, ubicacion_fisica=?, stock_actual=?, stock_minimo=?, precio=?
            WHERE id=?
        ''', (data['descripcion'], data['numero_serie'], data['ubicacion_fisica'], 
              data['stock_actual'], data['stock_minimo'], precio_nuevo, pieza_id))
        
        # Registrar cambio de precio en historial si cambió
        if precio_anterior != precio_nuevo:
            conn.execute('''
                INSERT INTO historial_precios (pieza_id, precio_anterior, precio_nuevo, usuario_id, motivo, observaciones)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (pieza_id, precio_anterior, precio_nuevo, session['user_id'], 
                  'Actualización manual', data.get('observaciones_precio', '')))
        
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

# Historial de Precios (U003)
@app.route('/historial-precios')
def historial_precios():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    piezas = conn.execute('SELECT id, descripcion, numero_serie FROM piezas ORDER BY descripcion').fetchall()
    conn.close()
    return render_template('historial_precios.html', piezas=piezas)

@app.route('/api/historial-precios')
def api_historial_precios():
    if 'user_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    
    conn = get_db_connection()
    
    # Parámetros de filtro
    pieza_id = request.args.get('pieza_id')
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')
    proveedor = request.args.get('proveedor')
    
    # Construir consulta base
    query = '''
        SELECT h.*, p.descripcion as pieza_desc, p.numero_serie, u.nombre as usuario_nombre
        FROM historial_precios h
        JOIN piezas p ON h.pieza_id = p.id
        JOIN usuarios u ON h.usuario_id = u.id
        WHERE 1=1
    '''
    params = []
    
    # Aplicar filtros
    if pieza_id:
        query += ' AND h.pieza_id = ?'
        params.append(pieza_id)
    
    if fecha_inicio:
        query += ' AND DATE(h.created_at) >= ?'
        params.append(fecha_inicio)
    
    if fecha_fin:
        query += ' AND DATE(h.created_at) <= ?'
        params.append(fecha_fin)
    
    if proveedor:
        query += ' AND h.proveedor LIKE ?'
        params.append(f'%{proveedor}%')
    
    query += ' ORDER BY h.created_at DESC'
    
    historial = conn.execute(query, params).fetchall()
    conn.close()
    
    return jsonify([dict(row) for row in historial])

@app.route('/api/historial-precios/estadisticas')
def api_historial_estadisticas():
    if 'user_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    
    conn = get_db_connection()
    
    pieza_id = request.args.get('pieza_id')
    
    if not pieza_id:
        return jsonify({'error': 'ID de pieza requerido'}), 400
    
    # Obtener estadísticas de la pieza
    estadisticas = conn.execute('''
        SELECT 
            MIN(precio_nuevo) as precio_minimo,
            MAX(precio_nuevo) as precio_maximo,
            AVG(precio_nuevo) as precio_promedio,
            COUNT(*) as total_cambios
        FROM historial_precios 
        WHERE pieza_id = ?
    ''', (pieza_id,)).fetchone()
    
    # Obtener último precio
    ultimo_cambio = conn.execute('''
        SELECT precio_nuevo, created_at 
        FROM historial_precios 
        WHERE pieza_id = ? 
        ORDER BY created_at DESC 
        LIMIT 1
    ''', (pieza_id,)).fetchone()
    
    # Obtener variación de precios por mes (últimos 12 meses)
    variacion_mensual = conn.execute('''
        SELECT 
            strftime('%Y-%m', created_at) as mes,
            AVG(precio_nuevo) as precio_promedio,
            COUNT(*) as cambios
        FROM historial_precios 
        WHERE pieza_id = ? 
        AND DATE(created_at) >= DATE('now', '-12 months')
        GROUP BY strftime('%Y-%m', created_at)
        ORDER BY mes
    ''', (pieza_id,)).fetchall()
    
    conn.close()
    
    return jsonify({
        'estadisticas': dict(estadisticas) if estadisticas else {},
        'ultimo_cambio': dict(ultimo_cambio) if ultimo_cambio else {},
        'variacion_mensual': [dict(row) for row in variacion_mensual]
    })

@app.route('/api/historial-precios/exportar')
def api_exportar_historial():
    if 'user_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    
    import csv
    from io import StringIO
    from flask import Response
    
    conn = get_db_connection()
    
    # Obtener los mismos filtros que la consulta principal
    pieza_id = request.args.get('pieza_id')
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')
    proveedor = request.args.get('proveedor')
    
    # Usar la misma consulta que la API principal
    query = '''
        SELECT h.*, p.descripcion as pieza_desc, p.numero_serie, u.nombre as usuario_nombre
        FROM historial_precios h
        JOIN piezas p ON h.pieza_id = p.id
        JOIN usuarios u ON h.usuario_id = u.id
        WHERE 1=1
    '''
    params = []
    
    if pieza_id:
        query += ' AND h.pieza_id = ?'
        params.append(pieza_id)
    
    if fecha_inicio:
        query += ' AND DATE(h.created_at) >= ?'
        params.append(fecha_inicio)
    
    if fecha_fin:
        query += ' AND DATE(h.created_at) <= ?'
        params.append(fecha_fin)
    
    if proveedor:
        query += ' AND h.proveedor LIKE ?'
        params.append(f'%{proveedor}%')
    
    query += ' ORDER BY h.created_at DESC'
    
    historial = conn.execute(query, params).fetchall()
    conn.close()
    
    # Crear CSV
    output = StringIO()
    writer = csv.writer(output)
    
    # Escribir encabezados
    writer.writerow([
        'ID', 'Pieza', 'Número Serie', 'Precio Anterior', 'Precio Nuevo', 
        'Diferencia', 'Proveedor', 'Motivo', 'Usuario', 'Fecha'
    ])
    
    # Escribir datos
    for row in historial:
        diferencia = row['precio_nuevo'] - (row['precio_anterior'] or 0)
        writer.writerow([
            row['id'],
            row['pieza_desc'],
            row['numero_serie'],
            f"${row['precio_anterior']:.2f}" if row['precio_anterior'] else 'N/A',
            f"${row['precio_nuevo']:.2f}",
            f"${diferencia:.2f}",
            row['proveedor'] or 'N/A',
            row['motivo'] or 'N/A',
            row['usuario_nombre'],
            row['created_at']
        ])
    
    output.seek(0)
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=historial_precios.csv"}
    )

# Reportes de Movimientos (U009)
@app.route('/reportes')
def reportes():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    piezas = conn.execute('SELECT id, descripcion, numero_serie FROM piezas ORDER BY descripcion').fetchall()
    usuarios = conn.execute('SELECT id, nombre FROM usuarios ORDER BY nombre').fetchall()
    conn.close()
    return render_template('reportes.html', piezas=piezas, usuarios=usuarios)

@app.route('/api/reportes/movimientos')
def api_reportes_movimientos():
    if 'user_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    
    conn = get_db_connection()
    
    # Parámetros de filtro
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')
    pieza_id = request.args.get('pieza_id')
    tipo_movimiento = request.args.get('tipo_movimiento')
    usuario_id = request.args.get('usuario_id')
    
    # Consulta unificada de movimientos (piezas y lotes)
    query_movimientos = '''
        SELECT 
            'pieza' as tipo_origen,
            m.id,
            m.created_at,
            p.descripcion as componente,
            p.numero_serie,
            p.ubicacion_fisica,
            m.tipo_movimiento,
            m.cantidad,
            m.observaciones,
            u.nombre as usuario_nombre,
            u.rol as usuario_rol,
            NULL as lote_numero,
            NULL as proveedor_lote
        FROM movimientos m
        JOIN piezas p ON m.pieza_id = p.id
        JOIN usuarios u ON m.usuario_id = u.id
        WHERE 1=1
    '''
    
    query_lotes = '''
        UNION ALL
        SELECT 
            'lote' as tipo_origen,
            ml.id,
            ml.created_at,
            p.descripcion as componente,
            p.numero_serie,
            p.ubicacion_fisica,
            ml.tipo_movimiento,
            ml.cantidad,
            ml.observaciones,
            u.nombre as usuario_nombre,
            u.rol as usuario_rol,
            l.numero_lote,
            l.proveedor as proveedor_lote
        FROM movimientos_lotes ml
        JOIN lotes l ON ml.lote_id = l.id
        JOIN piezas p ON l.pieza_id = p.id
        JOIN usuarios u ON ml.usuario_id = u.id
        WHERE 1=1
    '''
    
    params = []
    
    # Aplicar filtros a ambas consultas
    filtros_where = ''
    if fecha_inicio:
        filtros_where += ' AND DATE(m.created_at) >= ?'
        params.append(fecha_inicio)
    if fecha_fin:
        filtros_where += ' AND DATE(m.created_at) <= ?'
        params.append(fecha_fin)
    if pieza_id:
        filtros_where += ' AND p.id = ?'
        params.append(pieza_id)
    if tipo_movimiento:
        filtros_where += ' AND m.tipo_movimiento = ?'
        params.append(tipo_movimiento)
    if usuario_id:
        filtros_where += ' AND u.id = ?'
        params.append(usuario_id)
    
    # Construir consulta completa
    query_completa = query_movimientos + filtros_where
    
    # Ajustar filtros para consulta de lotes (cambiar m. por ml.)
    filtros_lotes = filtros_where.replace('m.created_at', 'ml.created_at')
    filtros_lotes = filtros_lotes.replace('m.tipo_movimiento', 'ml.tipo_movimiento')
    filtros_lotes = filtros_lotes.replace('u.id', 'u.id')
    
    query_completa += query_lotes + filtros_lotes
    query_completa += ' ORDER BY created_at DESC'
    
    # Duplicar parámetros para la segunda consulta
    params_completos = params + params
    
    movimientos = conn.execute(query_completa, params_completos).fetchall()
    conn.close()
    
    return jsonify([dict(mov) for mov in movimientos])

@app.route('/api/reportes/estadisticas')
def api_reportes_estadisticas():
    if 'user_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    
    conn = get_db_connection()
    
    # Parámetros de filtro
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')
    
    # Estadísticas generales
    stats_query = '''
        SELECT 
            COUNT(*) as total_movimientos,
            SUM(CASE WHEN tipo_movimiento = 'entrada' THEN cantidad ELSE 0 END) as total_entradas,
            SUM(CASE WHEN tipo_movimiento = 'salida' THEN cantidad ELSE 0 END) as total_salidas,
            COUNT(DISTINCT pieza_id) as piezas_involucradas,
            COUNT(DISTINCT usuario_id) as usuarios_activos
        FROM movimientos m
        WHERE 1=1
    '''
    
    params = []
    if fecha_inicio:
        stats_query += ' AND DATE(m.created_at) >= ?'
        params.append(fecha_inicio)
    if fecha_fin:
        stats_query += ' AND DATE(m.created_at) <= ?'
        params.append(fecha_fin)
    
    estadisticas = conn.execute(stats_query, params).fetchone()
    
    # Top 5 piezas con más movimientos
    top_piezas_query = '''
        SELECT 
            p.descripcion,
            p.numero_serie,
            COUNT(*) as cantidad_movimientos,
            SUM(m.cantidad) as cantidad_total
        FROM movimientos m
        JOIN piezas p ON m.pieza_id = p.id
        WHERE 1=1
    '''
    
    top_piezas_query += ''.join([' AND DATE(m.created_at) >= ?' if fecha_inicio else '',
                                 ' AND DATE(m.created_at) <= ?' if fecha_fin else ''])
    top_piezas_query += ' GROUP BY p.id ORDER BY cantidad_movimientos DESC LIMIT 5'
    
    top_piezas = conn.execute(top_piezas_query, params).fetchall()
    
    # Movimientos por día (últimos 30 días)
    movimientos_diarios = conn.execute('''
        SELECT 
            DATE(m.created_at) as fecha,
            COUNT(*) as cantidad_movimientos,
            SUM(CASE WHEN m.tipo_movimiento = 'entrada' THEN m.cantidad ELSE 0 END) as entradas,
            SUM(CASE WHEN m.tipo_movimiento = 'salida' THEN m.cantidad ELSE 0 END) as salidas
        FROM movimientos m
        WHERE DATE(m.created_at) >= DATE('now', '-30 days')
        GROUP BY DATE(m.created_at)
        ORDER BY fecha DESC
    ''').fetchall()
    
    # Movimientos por usuario
    movimientos_usuario = conn.execute('''
        SELECT 
            u.nombre,
            u.rol,
            COUNT(*) as cantidad_movimientos,
            SUM(m.cantidad) as cantidad_total
        FROM movimientos m
        JOIN usuarios u ON m.usuario_id = u.id
        WHERE 1=1
    ''' + ''.join([' AND DATE(m.created_at) >= ?' if fecha_inicio else '',
                   ' AND DATE(m.created_at) <= ?' if fecha_fin else '']) + '''
        GROUP BY u.id
        ORDER BY cantidad_movimientos DESC
    ''', params).fetchall()
    
    conn.close()
    
    return jsonify({
        'estadisticas_generales': dict(estadisticas),
        'top_piezas': [dict(p) for p in top_piezas],
        'movimientos_diarios': [dict(m) for m in movimientos_diarios],
        'movimientos_por_usuario': [dict(u) for u in movimientos_usuario]
    })

@app.route('/api/reportes/exportar-excel')
def api_exportar_excel():
    if 'user_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    
    try:
        import pandas as pd
        from io import BytesIO
        from flask import Response
        
        conn = get_db_connection()
        
        # Obtener los mismos filtros que la consulta principal
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        pieza_id = request.args.get('pieza_id')
        tipo_movimiento = request.args.get('tipo_movimiento')
        usuario_id = request.args.get('usuario_id')
        
        # Reutilizar la misma lógica de consulta
        query_movimientos = '''
            SELECT 
                'Pieza' as origen,
                m.created_at as fecha_hora,
                p.descripcion as componente,
                p.numero_serie,
                p.ubicacion_fisica,
                m.tipo_movimiento,
                m.cantidad,
                m.observaciones,
                u.nombre as usuario,
                u.rol as rol_usuario,
                '' as numero_lote,
                '' as proveedor
            FROM movimientos m
            JOIN piezas p ON m.pieza_id = p.id
            JOIN usuarios u ON m.usuario_id = u.id
            WHERE 1=1
        '''
        
        query_lotes = '''
            UNION ALL
            SELECT 
                'Lote' as origen,
                ml.created_at as fecha_hora,
                p.descripcion as componente,
                p.numero_serie,
                p.ubicacion_fisica,
                ml.tipo_movimiento,
                ml.cantidad,
                ml.observaciones,
                u.nombre as usuario,
                u.rol as rol_usuario,
                l.numero_lote,
                l.proveedor
            FROM movimientos_lotes ml
            JOIN lotes l ON ml.lote_id = l.id
            JOIN piezas p ON l.pieza_id = p.id
            JOIN usuarios u ON ml.usuario_id = u.id
            WHERE 1=1
        '''
        
        params = []
        filtros_where = ''
        if fecha_inicio:
            filtros_where += ' AND DATE(m.created_at) >= ?'
            params.append(fecha_inicio)
        if fecha_fin:
            filtros_where += ' AND DATE(m.created_at) <= ?'
            params.append(fecha_fin)
        if pieza_id:
            filtros_where += ' AND p.id = ?'
            params.append(pieza_id)
        if tipo_movimiento:
            filtros_where += ' AND m.tipo_movimiento = ?'
            params.append(tipo_movimiento)
        if usuario_id:
            filtros_where += ' AND u.id = ?'
            params.append(usuario_id)
        
        query_completa = query_movimientos + filtros_where
        filtros_lotes = filtros_where.replace('m.created_at', 'ml.created_at')
        filtros_lotes = filtros_lotes.replace('m.tipo_movimiento', 'ml.tipo_movimiento')
        query_completa += query_lotes + filtros_lotes
        query_completa += ' ORDER BY fecha_hora DESC'
        
        params_completos = params + params
        
        # Ejecutar consulta y crear DataFrame
        movimientos = conn.execute(query_completa, params_completos).fetchall()
        
        # Convertir a DataFrame
        df = pd.DataFrame([dict(mov) for mov in movimientos])
        
        if df.empty:
            conn.close()
            return jsonify({'error': 'No hay datos para exportar'}), 400
        
        # Crear archivo Excel en memoria
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Hoja principal con movimientos
            df.to_excel(writer, sheet_name='Movimientos', index=False)
            
            # Hoja de estadísticas
            stats_data = {
                'Métrica': ['Total Movimientos', 'Total Entradas', 'Total Salidas', 'Piezas Involucradas'],
                'Valor': [
                    len(df),
                    len(df[df['tipo_movimiento'] == 'entrada']),
                    len(df[df['tipo_movimiento'] == 'salida']),
                    df['componente'].nunique()
                ]
            }
            stats_df = pd.DataFrame(stats_data)
            stats_df.to_excel(writer, sheet_name='Estadísticas', index=False)
        
        output.seek(0)
        conn.close()
        
        return Response(
            output.getvalue(),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition': 'attachment; filename=reporte_movimientos.xlsx'}
        )
        
    except ImportError:
        return jsonify({'error': 'Pandas no está instalado. Usando exportación CSV.'}), 400
    except Exception as e:
        return jsonify({'error': f'Error al generar Excel: {str(e)}'}), 500

@app.route('/api/reportes/exportar-pdf')
def api_exportar_pdf():
    if 'user_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from io import BytesIO
        from datetime import datetime
        from flask import Response
        
        conn = get_db_connection()
        
        # Obtener filtros
        fecha_inicio = request.args.get('fecha_inicio', '')
        fecha_fin = request.args.get('fecha_fin', '')
        pieza_id = request.args.get('pieza_id')
        tipo_movimiento = request.args.get('tipo_movimiento', '')
        usuario_id = request.args.get('usuario_id')
        
        # Obtener datos simplificados para PDF
        query = '''
            SELECT 
                DATE(m.created_at) as fecha,
                p.descripcion as componente,
                m.tipo_movimiento,
                m.cantidad,
                u.nombre as usuario
            FROM movimientos m
            JOIN piezas p ON m.pieza_id = p.id
            JOIN usuarios u ON m.usuario_id = u.id
            WHERE 1=1
        '''
        
        params = []
        if fecha_inicio:
            query += ' AND DATE(m.created_at) >= ?'
            params.append(fecha_inicio)
        if fecha_fin:
            query += ' AND DATE(m.created_at) <= ?'
            params.append(fecha_fin)
        if pieza_id:
            query += ' AND p.id = ?'
            params.append(pieza_id)
        if tipo_movimiento:
            query += ' AND m.tipo_movimiento = ?'
            params.append(tipo_movimiento)
        if usuario_id:
            query += ' AND u.id = ?'
            params.append(usuario_id)
        
        query += ' ORDER BY m.created_at DESC LIMIT 100'  # Limitar para PDF
        
        movimientos = conn.execute(query, params).fetchall()
        conn.close()
        
        # Crear PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
        
        # Estilos
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=1  # Centro
        )
        
        # Contenido
        story = []
        
        # Título
        title = Paragraph("Reporte de Movimientos de Inventario<br/>Maestranzas Unidos S.A.", title_style)
        story.append(title)
        
        # Información del reporte
        info_text = f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}<br/>"
        if fecha_inicio and fecha_fin:
            info_text += f"Período: {fecha_inicio} al {fecha_fin}<br/>"
        if tipo_movimiento:
            info_text += f"Tipo: {tipo_movimiento.title()}<br/>"
        info_text += f"Total de registros: {len(movimientos)}"
        
        info = Paragraph(info_text, styles['Normal'])
        story.append(info)
        story.append(Spacer(1, 20))
        
        if movimientos:
            # Tabla de datos
            data = [['Fecha', 'Componente', 'Tipo', 'Cantidad', 'Usuario']]
            
            for mov in movimientos:
                data.append([
                    mov['fecha'],
                    mov['componente'][:30] + '...' if len(mov['componente']) > 30 else mov['componente'],
                    mov['tipo_movimiento'].title(),
                    str(mov['cantidad']),
                    mov['usuario']
                ])
            
            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(table)
        else:
            no_data = Paragraph("No se encontraron movimientos con los filtros aplicados.", styles['Normal'])
            story.append(no_data)
        
        doc.build(story)
        
        buffer.seek(0)
        
        return Response(
            buffer.getvalue(),
            mimetype='application/pdf',
            headers={'Content-Disposition': 'attachment; filename=reporte_movimientos.pdf'}
        )
        
    except ImportError:
        return jsonify({'error': 'ReportLab no está instalado para generar PDF.'}), 400
    except Exception as e:
        return jsonify({'error': f'Error al generar PDF: {str(e)}'}), 500

# Lotes y Vencimientos (U007)
@app.route('/lotes')
def lotes():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    lotes = conn.execute('''
        SELECT l.*, p.descripcion as pieza_desc, p.numero_serie
        FROM lotes l
        JOIN piezas p ON l.pieza_id = p.id
        ORDER BY l.fecha_vencimiento ASC
    ''').fetchall()
    conn.close()
    return render_template('lotes.html', lotes=lotes)

@app.route('/api/lotes', methods=['GET', 'POST'])
def api_lotes():
    if 'user_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    
    conn = get_db_connection()
    
    if request.method == 'POST':
        data = request.get_json()
        conn.execute('''
            INSERT INTO lotes (pieza_id, numero_lote, fecha_fabricacion, fecha_vencimiento, 
                              cantidad_inicial, cantidad_actual, proveedor, observaciones)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (data['pieza_id'], data['numero_lote'], data.get('fecha_fabricacion'), 
              data['fecha_vencimiento'], data['cantidad_inicial'], data['cantidad_inicial'],
              data.get('proveedor', ''), data.get('observaciones', '')))
        
        lote_id = conn.lastrowid
        
        # Actualizar stock de la pieza
        conn.execute('UPDATE piezas SET stock_actual = stock_actual + ? WHERE id = ?', 
                    (data['cantidad_inicial'], data['pieza_id']))
        
        # Registrar movimiento inicial
        conn.execute('''
            INSERT INTO movimientos_lotes (lote_id, tipo_movimiento, cantidad, usuario_id, observaciones)
            VALUES (?, ?, ?, ?, ?)
        ''', (lote_id, 'entrada', data['cantidad_inicial'], session['user_id'], 
              f'Lote inicial: {data["numero_lote"]}'))
        
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'lote_id': lote_id})
    
    lotes = conn.execute('''
        SELECT l.*, p.descripcion as pieza_desc, p.numero_serie
        FROM lotes l
        JOIN piezas p ON l.pieza_id = p.id
        ORDER BY l.fecha_vencimiento ASC
    ''').fetchall()
    conn.close()
    return jsonify([dict(lote) for lote in lotes])

@app.route('/api/lotes/<int:lote_id>', methods=['PUT', 'DELETE'])
def api_lote_detail(lote_id):
    if 'user_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    
    conn = get_db_connection()
    
    if request.method == 'PUT':
        data = request.get_json()
        conn.execute('''
            UPDATE lotes 
            SET numero_lote=?, fecha_fabricacion=?, fecha_vencimiento=?, proveedor=?, observaciones=?
            WHERE id=?
        ''', (data['numero_lote'], data.get('fecha_fabricacion'), data['fecha_vencimiento'], 
              data.get('proveedor', ''), data.get('observaciones', ''), lote_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    elif request.method == 'DELETE':
        # Verificar que el lote esté vacío antes de eliminar
        lote = conn.execute('SELECT * FROM lotes WHERE id=?', (lote_id,)).fetchone()
        if lote and lote['cantidad_actual'] > 0:
            conn.close()
            return jsonify({'error': 'No se puede eliminar un lote con stock disponible'}), 400
        
        conn.execute('UPDATE lotes SET estado = ? WHERE id=?', ('eliminado', lote_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True})

@app.route('/api/lotes/<int:lote_id>/movimiento', methods=['POST'])
def api_lote_movimiento(lote_id):
    if 'user_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    
    data = request.get_json()
    conn = get_db_connection()
    
    lote = conn.execute('SELECT * FROM lotes WHERE id=?', (lote_id,)).fetchone()
    if not lote:
        conn.close()
        return jsonify({'error': 'Lote no encontrado'}), 404
    
    tipo_movimiento = data['tipo_movimiento']
    cantidad = data['cantidad']
    
    # Validaciones
    if tipo_movimiento == 'salida' and cantidad > lote['cantidad_actual']:
        conn.close()
        return jsonify({'error': 'Cantidad insuficiente en el lote'}), 400
    
    # Verificar fecha de vencimiento
    from datetime import datetime, date
    fecha_vencimiento = datetime.strptime(lote['fecha_vencimiento'], '%Y-%m-%d').date()
    if fecha_vencimiento < date.today():
        # Crear alerta de vencimiento si no existe
        alerta_existente = conn.execute('''
            SELECT id FROM alertas WHERE lote_id=? AND tipo_alerta='vencido' AND estado='activa'
        ''', (lote_id,)).fetchone()
        
        if not alerta_existente:
            conn.execute('''
                INSERT INTO alertas (lote_id, pieza_id, tipo_alerta, mensaje)
                VALUES (?, ?, ?, ?)
            ''', (lote_id, lote['pieza_id'], 'vencido', 
                  f'Lote vencido: {lote["numero_lote"]} (Vencido el {lote["fecha_vencimiento"]})'))
    
    # Registrar movimiento del lote
    conn.execute('''
        INSERT INTO movimientos_lotes (lote_id, tipo_movimiento, cantidad, usuario_id, observaciones)
        VALUES (?, ?, ?, ?, ?)
    ''', (lote_id, tipo_movimiento, cantidad, session['user_id'], data.get('observaciones', '')))
    
    # Actualizar cantidad del lote
    if tipo_movimiento == 'entrada':
        new_cantidad = lote['cantidad_actual'] + cantidad
        conn.execute('UPDATE piezas SET stock_actual = stock_actual + ? WHERE id = ?', 
                    (cantidad, lote['pieza_id']))
    else:  # salida
        new_cantidad = lote['cantidad_actual'] - cantidad
        conn.execute('UPDATE piezas SET stock_actual = stock_actual - ? WHERE id = ?', 
                    (cantidad, lote['pieza_id']))
    
    conn.execute('UPDATE lotes SET cantidad_actual = ? WHERE id = ?', (new_cantidad, lote_id))
    
    # Verificar alertas de stock bajo en la pieza
    pieza = conn.execute('SELECT * FROM piezas WHERE id = ?', (lote['pieza_id'],)).fetchone()
    if pieza['stock_actual'] <= pieza['stock_minimo']:
        alerta_stock_existente = conn.execute('''
            SELECT id FROM alertas WHERE pieza_id=? AND tipo_alerta='stock_minimo' AND estado='activa'
        ''', (lote['pieza_id'],)).fetchone()
        
        if not alerta_stock_existente:
            conn.execute('''
                INSERT INTO alertas (pieza_id, tipo_alerta, mensaje)
                VALUES (?, ?, ?)
            ''', (lote['pieza_id'], 'stock_minimo', f'Stock bajo: {pieza["descripcion"]}'))
    
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/lotes/vencimientos')
def api_lotes_vencimientos():
    if 'user_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    
    conn = get_db_connection()
    
    # Obtener lotes próximos a vencer (30 días)
    from datetime import datetime, timedelta
    fecha_limite = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    
    lotes_vencimiento = conn.execute('''
        SELECT l.*, p.descripcion as pieza_desc, p.numero_serie
        FROM lotes l
        JOIN piezas p ON l.pieza_id = p.id
        WHERE l.fecha_vencimiento <= ? AND l.cantidad_actual > 0 AND l.estado = 'activo'
        ORDER BY l.fecha_vencimiento ASC
    ''', (fecha_limite,)).fetchall()
    
    conn.close()
    return jsonify([dict(lote) for lote in lotes_vencimiento])

@app.route('/api/verificar-vencimientos', methods=['POST'])
def verificar_vencimientos():
    """Función para verificar y crear alertas de vencimientos automáticamente"""
    if 'user_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    
    conn = get_db_connection()
    
    from datetime import datetime, timedelta, date
    hoy = date.today()
    fecha_alerta = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    
    # Buscar lotes próximos a vencer
    lotes_proximos = conn.execute('''
        SELECT l.*, p.descripcion as pieza_desc
        FROM lotes l
        JOIN piezas p ON l.pieza_id = p.id
        WHERE l.fecha_vencimiento <= ? AND l.cantidad_actual > 0 AND l.estado = 'activo'
    ''', (fecha_alerta,)).fetchall()
    
    alertas_creadas = 0
    
    for lote in lotes_proximos:
        fecha_vencimiento = datetime.strptime(lote['fecha_vencimiento'], '%Y-%m-%d').date()
        dias_restantes = (fecha_vencimiento - hoy).days
        
        # Verificar si ya existe una alerta activa para este lote
        alerta_existente = conn.execute('''
            SELECT id FROM alertas WHERE lote_id=? AND tipo_alerta IN ('proximo_vencimiento', 'vencido') AND estado='activa'
        ''', (lote['id'],)).fetchone()
        
        if not alerta_existente:
            if dias_restantes < 0:
                # Lote vencido
                mensaje = f'Lote VENCIDO: {lote["numero_lote"]} de {lote["pieza_desc"]} (Vencido hace {abs(dias_restantes)} días)'
                tipo_alerta = 'vencido'
            else:
                # Lote próximo a vencer
                mensaje = f'Lote próximo a vencer: {lote["numero_lote"]} de {lote["pieza_desc"]} (Vence en {dias_restantes} días)'
                tipo_alerta = 'proximo_vencimiento'
            
            conn.execute('''
                INSERT INTO alertas (lote_id, pieza_id, tipo_alerta, mensaje)
                VALUES (?, ?, ?, ?)
            ''', (lote['id'], lote['pieza_id'], tipo_alerta, mensaje))
            alertas_creadas += 1
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'alertas_creadas': alertas_creadas})

if __name__ == '__main__':
    init_db()
    app.run(debug=True) 