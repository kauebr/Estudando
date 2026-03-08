############################################################################################################################################################
# Código ETL leads2b
# versão API L2b: v1
############################################################################################################################################################

# IMPORTANDO BIBLIOTECAS
############################################################################################################################################################
import pandas as pd
import requests
from datetime import datetime, timedelta


############################################################################################################################################################
# FUNÇÕES
############################################################################################################################################################
def dinamite(json_data):
    # Normalizando o JSON inicial
    df = pd.json_normalize(json_data, sep='_', errors='ignore')
    
    # Loop para explodir listas aninhadas automaticamente
    while True:
        col_to_explode = next(
            (col for col in df.columns if df[col].apply(lambda x: isinstance(x, list) and len(x) > 0).any()),
            None
        )

        if col_to_explode is None:
            break

        df = df.explode(col_to_explode).reset_index(drop=True)

        if df[col_to_explode].notna().any() and isinstance(df[col_to_explode].dropna().iloc[0], dict):
            new_columns = pd.json_normalize(df[col_to_explode].dropna(), sep='_')
            new_columns = new_columns.add_prefix(f"{col_to_explode}_")
            df = df.drop(columns=[col_to_explode]).join(new_columns, how='left')

    # Converte listas restantes para string
    for col in df.columns:
        if df[col].apply(lambda x: isinstance(x, list)).any():
            df[col] = df[col].apply(lambda x: str(x) if isinstance(x, list) else x)

    df = df.drop_duplicates()
    return df


def start_date() -> str:
    return (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d %H:%M:%S')

############################################################################################################################################################
# LISTANDO ENDPOINTS
############################################################################################################################################################
url_raiz = 'https://app.leads2b.com'

urls = {
    'clientes'     : f'{url_raiz}/api/v1/customers/list',
    'produtos'     : f'{url_raiz}/api/v1/items/list',
    'pedidos'      : f'{url_raiz}/api/v1/items/list',
    'prospect'     : f'{url_raiz}/api/v1/prospect/list',
    'leads'        : f'{url_raiz}/api/v1/leads/list',
    'oportunidades': f'{url_raiz}/api/v1/opportunities/list'
}

############################################################################################################################################################
# AUTENTICAÇÃO
############################################################################################################################################################
token = '****************************************************************************************'

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}



############################################################################################################################################################
# 3 EXPLODINDO LEADS — REFATORADO
############################################################################################################################################################

df_leads = pd.DataFrame()

# Datas iniciais
finish_date = datetime.now()
start_date  = finish_date - timedelta(days=90)

# Limite mínimo para parar (ano 2023)
limite_ano = datetime(2023, 1, 1)

meta = [
    "city", "cnpj", "company_name", "customer_company_name", "customer_id",
    "customer_name", "custom_fields", "email", "fk_id", "lead_created_at",
    "lead_id", "lead_name", "lead_responsable", "lead_responsable_id",
    "lead_status", "list_id", "loss_reason", "lost_at", "main_contact",
    "main_email", "main_phone", "opportunity_created_at", "opportunity_id",
    "opportunity_status", "order_date", "order_total", "origin", "phone",
    "pipeline", "pipeline_step", "rdstation_uuid", "state", "tags"
]

# Loop voltando no tempo
while start_date >= limite_ano:

    print(f"\n⏳ Coletando período: {start_date} -> {finish_date}")

    params = {
        'start_at': start_date.strftime('%Y-%m-%d %H:%M:%S'),
        'finish_at': finish_date.strftime('%Y-%m-%d %H:%M:%S'),
        'limit': 200,
        'offset': 1
    }

    while True:
        response = requests.get(urls['leads'], headers=headers, params=params)
        response_json = response.json()

        # Se API não retornar result, parar
        if 'result' not in response_json:
            break

        resultados = response_json['result']
        tamanho = len(resultados)

        print(f"-> Offset {params['offset']} | retornado: {tamanho}")

        # Se retornar menos que 1, acabou esse período
        if tamanho < 1:
            break

        # Normalização dos dados
        for lead in resultados:
            df_aux = pd.json_normalize(
                lead,
                record_path=['tags'],
                meta=meta,
                meta_prefix='meta_',
                errors='ignore'
            )
            df_leads = pd.concat([df_leads, df_aux], ignore_index=True)

        # Próxima página
        params['offset'] += 1

    # Atualiza intervalo para voltar 3 meses
    finish_date = start_date
    start_date = finish_date - timedelta(days=90)

print("\n✅ Coleta finalizada!")
print("Total de linhas:", len(df_leads))
