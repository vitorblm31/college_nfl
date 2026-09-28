from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import pandas as pd
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def conectar_banco():
    return sqlite3.connect('nfl_draft_scouting.db')

@app.get("/api/jogadores")
def listar_jogadores():
    conexao = conectar_banco()
    query = "SELECT DISTINCT player_name FROM combine_metrics WHERE player_name IS NOT NULL ORDER BY player_name"
    df = pd.read_sql_query(query, conexao)
    conexao.close()
    return {"jogadores": df['player_name'].tolist()}

@app.get("/api/jogador/{nome}")
def obter_perfil_jogador(nome: str):
    conexao = conectar_banco()
    conexao.row_factory = sqlite3.Row 
    cursor = conexao.cursor()
    
    query_combine = """
        SELECT 
            player_name, 
            ht AS height, 
            wt AS weight, 
            forty AS forty_yard_dash, 
            vertical AS vertical_jump, 
            broad_jump 
        FROM combine_metrics 
        WHERE player_name = ? LIMIT 1
    """
    
    try:
        cursor.execute(query_combine, (nome,))
        linha_combine = cursor.fetchone()
    except Exception as e:
        conexao.close()
        return {"erro": f"Falha na consulta SQL: {e}"}
        
    if linha_combine is None:
        conexao.close()
        return {"erro": "Jogador não encontrado"}

    dados_completos = dict(linha_combine)

    query_stats = """
        SELECT receptions, receiving_yards, receiving_tds 
        FROM college_stats 
        WHERE player_name = ? LIMIT 1
    """
    
    try:
        cursor.execute(query_stats, (nome,))
        linha_stats = cursor.fetchone()
        
        if linha_stats:
            dados_completos.update(dict(linha_stats))
        else:
            dados_completos.update({"receptions": 0, "receiving_yards": 0, "receiving_tds": 0})
    except sqlite3.OperationalError:
        dados_completos.update({"receptions": "N/D", "receiving_yards": "N/D", "receiving_tds": "N/D"})
    finally:
        conexao.close()
        
    return dados_completos

@app.get("/api/top10/{criterio}")
def obter_top10(criterio: str):
    conexao = conectar_banco()
    
    colunas_map = {
        "velocidade": ("combine_metrics", "forty", "ASC"), 
        "altura": ("combine_metrics", "ht", "DESC"),
        "peso": ("combine_metrics", "wt", "DESC"),
        "vertical": ("combine_metrics", "vertical", "DESC"),
        "distancia": ("combine_metrics", "broad_jump", "DESC"),
        "jardas": ("college_stats", "receiving_yards", "DESC"),
        "touchdowns": ("college_stats", "receiving_tds", "DESC"),
        "rececoes": ("college_stats", "receptions", "DESC")
    }
    
    if criterio not in colunas_map:
        conexao.close()
        return {"erro": "Critério inválido"}
        
    tabela, coluna, ordem = colunas_map[criterio]
    
    query = f"""
        SELECT player_name, {coluna} AS valor 
        FROM {tabela} 
        WHERE {coluna} IS NOT NULL 
        ORDER BY {coluna} {ordem} 
        LIMIT 10
    """
    
    df = pd.read_sql_query(query, conexao)
    conexao.close()
    
    return {"criterio": criterio, "ranking": df.to_dict(orient="records")}

if __name__ == "__main__":
    uvicorn.run("api:app", host="127.0.0.1", port=int(os.environ.get("PORT", 8000)), reload=True)