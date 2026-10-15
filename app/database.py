"""SQLite data layer. CSV columns are preserved as strings; SQL casts numeric values when needed."""
import csv, sqlite3, zipfile
from pathlib import Path
from .settings import DATA_ZIP, DB_PATH

TABLES = ['customers','policies','claims','claim_documents','hospitals','customer_interactions']

def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=60)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA foreign_keys=OFF')
    return conn

def initialize_database(force=False):
    if not DATA_ZIP.exists():
        raise FileNotFoundError(f'Dataset archive not found: {DATA_ZIP}. Place data.zip in project root.')
    if DB_PATH.exists() and not force:
        conn=connect()
        try:
            existing={r['name'] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if set(TABLES).issubset(existing): return 'Database already initialized.'
        finally: conn.close()
    if DB_PATH.exists(): DB_PATH.unlink()
    conn=connect()
    try:
        with zipfile.ZipFile(DATA_ZIP) as z:
            for table in TABLES:
                filename=f'{table}.csv'
                with z.open(filename) as raw:
                    import io
                    reader=csv.DictReader(io.TextIOWrapper(raw, encoding='utf-8-sig', newline=''))
                    cols=reader.fieldnames
                    if not cols: continue
                    qcols=', '.join('"'+c.replace('"','""')+'" TEXT' for c in cols)
                    conn.execute(f'CREATE TABLE "{table}" ({qcols})')
                    placeholders=', '.join(['?']*len(cols))
                    sql=f'INSERT INTO "{table}" VALUES ({placeholders})'
                    batch=[]
                    for row in reader:
                        batch.append([row.get(c) for c in cols])
                        if len(batch)>=5000:
                            conn.executemany(sql,batch); batch=[]
                    if batch: conn.executemany(sql,batch)
                conn.commit()
        # Indexes make the common lookups fast.
        for statement in [
            'CREATE INDEX IF NOT EXISTS idx_claims_id ON claims(claim_id)',
            'CREATE INDEX IF NOT EXISTS idx_claims_customer ON claims(customer_id)',
            'CREATE INDEX IF NOT EXISTS idx_claims_policy ON claims(policy_id)',
            'CREATE INDEX IF NOT EXISTS idx_policies_id ON policies(policy_id)',
            'CREATE INDEX IF NOT EXISTS idx_policies_customer ON policies(customer_id)',
            'CREATE INDEX IF NOT EXISTS idx_docs_claim ON claim_documents(claim_id)',
            'CREATE INDEX IF NOT EXISTS idx_hospitals_id ON hospitals(hospital_id)',
            'CREATE INDEX IF NOT EXISTS idx_customers_id ON customers(customer_id)',
            'CREATE INDEX IF NOT EXISTS idx_interactions_claim ON customer_interactions(claim_id)',
        ]: conn.execute(statement)
        conn.commit()
    finally: conn.close()
    return 'Database imported successfully.'

def query(sql, params=()):
    conn=connect()
    try: return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally: conn.close()

def table_counts():
    out={}
    for t in TABLES:
        rows=query(f'SELECT COUNT(*) AS n FROM "{t}"')
        out[t]=rows[0]['n'] if rows else 0
    return out
