import numpy as np
from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
from datetime import timedelta
import csv
import matplotlib.pyplot as plt
import io
import base64
import pandas as pd

USERNAME = "admin"
PASSWORD = "password"
app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Usato per firmare la sessione
app.config['SESSION_PERMANENT'] = True  # Imposta la sessione come permanente (usa il timeout)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=5)  # Timeout di 5 minuti
# Configurazione della connessione al database MySQL
db_config = {
    'user': 'root',
    'password': '',
    'host': 'localhost',
    'database': 'PyDb'
}


@app.route('/')
def index():
    if 'username' in session:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM prodottipets")
        prodotti = cursor.fetchall()

        # utilizzo libreria pandas per dati
        pd.set_option('display.max_columns', None)

        cursor.execute( "SELECT id, nome, marca, pezzi, pezziVenduti  FROM prodottipets")
        ris = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description]
        df = pd.DataFrame(ris, columns=column_names)
        cursor.close()
        conn.close()

        sommaP = df['pezzi'].sum()
        sommaV = df['pezziVenduti'].sum()
        new_row = {
            'id': np.nan,  # Imposta su NaN o su un valore predefinito
            'nome': np.nan,  # Imposta su NaN o su un valore predefinito
            'marca': "Somma",  # Imposta su NaN o su un valore predefinito
            'pezzi': sommaP,  # Valore specificato
            'pezziVenduti': sommaV  # Valore specificato
        }
        new_row_df = pd.DataFrame([new_row])
        mediaP = df['pezzi'].mean()
        mediaV = df['pezziVenduti'].mean()
        new_row ={
            'id': np.nan,
            'nome': np.nan,
            'marca': "Media",
            'pezzi': mediaP,
            'pezziVenduti': mediaV
        }
        new_row_df1 = pd.DataFrame([new_row])

        # Aggiungere la nuova riga usando pd.concat
        df = pd.concat([df, new_row_df], ignore_index=True)
        df = pd.concat([df, new_row_df1], ignore_index=True)
        lista_prodotti = df.values.tolist()

        # Calcolare l'indice del prodotto più venduto, escludendo l'ultima riga
        index_max = df['pezziVenduti'][:-2].idxmax()  # Prende solo le righe fino all'ultima
        prodotto_piu_venduto = df.loc[index_max]
        prodottoMax = prodotto_piu_venduto['nome']
        index_min = df['pezziVenduti'][:-2].idxmin()  # Prende solo le righe fino all'ultima
        prodotto_meno_venduto = df.loc[index_min]
        prodottomin = prodotto_meno_venduto['nome']

        return render_template('gestore2.html', prodotti=prodotti, categorie=["Cibo", "Giocattoli", "Accessori"]
                               , lista=lista_prodotti, prodottoMax=prodottoMax, prodottoMin=prodottomin)
    else:
        return redirect(url_for('login'))


@app.route('/aggiungi', methods=['POST'])
def aggiungi():
    nome = request.form.get('nome')
    marca = request.form.get('marca')
    prezzo = float(request.form.get('prezzo'))
    url = request.form.get('url')
    quantita = int(request.form.get('quantita'))
    categoria = request.form.get('categoria')

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO prodottipets (nome, marca, prezzo,categoria, url, pezzi) VALUES (%s, %s, %s, %s, %s, %s)",
                   (nome, marca, prezzo, categoria, url, quantita))
    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for('index'))


@app.route('/elimina/<int:prodotto_id>')
def elimina(prodotto_id):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM prodottipets WHERE id = %s", (prodotto_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('index'))


@app.route('/modifica/<int:prodotto_id>', methods=['POST'])
def modifica(prodotto_id):
    nuova_quantita = int(request.form.get('quantita'))
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("UPDATE prodottipets SET pezzi = %s WHERE id = %s", (nuova_quantita, prodotto_id))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('index'))


@app.route('/categoria', methods=['GET'])
def categoria():
    categoria_selezionata = request.args.get('categoria')
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM prodottipets WHERE categoria = %s", (categoria_selezionata,))
    prodotti_categoria = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('gestore2.html', prodotti=prodotti_categoria, categorie=["Cibo", "Giocattoli", "Accessori"])


@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Verifica le credenziali dell'utente
        if username == USERNAME and password == PASSWORD:
            session['username'] = username  # Memorizza l'utente nella sessione
            return redirect(url_for('index'))  # Reindirizza all'area protetta
        else:
            return "Credenziali non valide"

    return render_template("login.html")

@app.route('/logout', methods=['POST'])
def automatic_logout():
    with app.app_context():
        session.pop('username', None)
        session.pop('password', None)
        return '', 204

@app.before_request
def make_session_permanent():
    session.permanent = True
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=5)

@app.route("/genera-file", methods=['GET'])
def genera_file():
    # Nome del file CSV
    file_csv = 'prodotti.csv'

    # Scrivi i dati nel file CSV
    with open(file_csv, mode='w', newline='') as file:
        writer = csv.writer(file)

        # Scrivi l'intestazione (opzionale)
        writer.writerow(['id', 'nome', 'marca', 'prezzo', 'categoria', 'url', 'pezzi',' pezzi venduti'])  # Modifica in base alle tue colonne

        # Scrivi i dati
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM prodottipets")
        prodotti = cursor.fetchall()
        cursor.close()
        conn.close()
        for prodotto in prodotti:
            writer.writerow([
                prodotto['id'],
                prodotto['nome'],
                prodotto['marca'],
                prodotto['prezzo'],
                prodotto['categoria'],
                prodotto['url'],
                prodotto['pezzi']
            ])

    return f"File {file_csv} creato con successo!"


@app.route('/store', methods=['GET', 'POST'])
def store():
    if 'username' not in session:
        return redirect(url_for('login'))

    # Recupera la modalità di visualizzazione dalla richiesta
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM prodottipets")
    prodotti = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('store1.html', prodotti=prodotti)

@app.route('/seleziona_prodotti', methods=['POST'])
def seleziona_prodotti():
    prodotti_selezionati = request.form.getlist('selezionati')
    quantita_prodotti = {}

    for prodotto_id in prodotti_selezionati:
        quantita = request.form.get(f'quantita_{prodotto_id}')
        quantita_prodotti[prodotto_id] = int(quantita)


    if 'carrello' not in session:
        session['carrello'] = {}

    for prodotto_id, quantita in quantita_prodotti.items():
        if prodotto_id in session['carrello']:
            session['carrello'][prodotto_id] += quantita
        else:
            session['carrello'][prodotto_id] = quantita

    return redirect(url_for('store'))


@app.route('/carrello', methods=['GET'])
def carrello():
    carrello_prodotti = []
    total_price = 0

    if 'carrello' in session:
        for prodotto_id, quantita in session['carrello'].items():
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM prodottipets WHERE id = %s", (prodotto_id,))
            prodotto = cursor.fetchone()
            cursor.close()
            conn.close()

            if prodotto:
                prodotto['quantita'] = quantita
                carrello_prodotti.append(prodotto)
                total_price += prodotto['prezzo'] * quantita

    return render_template('carrello.html', carrello_prodotti=carrello_prodotti, total_price=total_price)


@app.route('/acquista', methods=['POST'])
def acquista():
    if 'carrello' in session:
        for prodotto_id, quantita in session['carrello'].items():
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute("UPDATE prodottipets SET pezzi = pezzi - %s, pezziVenduti = pezziVenduti + %s WHERE id = %s",
                           (quantita, quantita, prodotto_id))
            conn.commit()
            cursor.close()
            conn.close()

        # Pulisci il carrello dopo l'acquisto
        session.pop('carrello', None)

    return redirect(url_for('store'))


@app.route('/rimuovi_dal_carrello/<int:prodotto_id>', methods=['GET'])
def rimuovi_dal_carrello(prodotto_id):
    if 'carrello' in session:
        if str(prodotto_id) in session['carrello']:
            del session['carrello'][str(prodotto_id)]

    return redirect(url_for('carrello'))

@app.route('/grafico_prezzi', methods=['GET'])
def grafico_prezzi():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT nome, pezzi FROM prodottipets")
    prodotti = cursor.fetchall()
    cursor.close()
    conn.close()

    # Estrai i nomi e i pezzi per il grafico
    nomi_prodotti = [prodotto['nome'] for prodotto in prodotti]
    pezzi_prodotti = [prodotto['pezzi'] for prodotto in prodotti]

    # Crea il grafico a torta
    plt.figure(figsize=(10, 6))
    plt.pie(pezzi_prodotti, labels=nomi_prodotti, autopct='%1.1f%%', startangle=140)
    plt.axis('equal')  # Per avere un cerchio perfetto

    # Salva il grafico in un'immagine in memoria
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    grafico_url = base64.b64encode(img.getvalue()).decode('utf8')
    plt.close()  # Chiudi la figura per liberare memoria

    return render_template('grafico.html', grafico_url=grafico_url)

if __name__ == '__main__':
    app.run(debug=True)