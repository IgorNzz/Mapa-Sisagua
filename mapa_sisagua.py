import pandas as pd
import geopandas as gpd
import folium
from folium.features import GeoJsonTooltip
from folium import IFrame

# === Caminhos dos arquivos ===
caminho_csv = r"C:\Users\Igor Natan\Documents\nome_da_pasta\Sisagua\dados_exportados.csv"
caminho_geojson = r"C:\Users\Igor Natan\Desktop\Shape\Delimitação_dos_Bairros_-_Dec._32.791_2020.geojson"
saida_html = r"C:\Users\Igor Natan\Documents\trab\mapa_resultado_com_denuncias.html"

# === Leitura dos dados ===
df = pd.read_csv(caminho_csv, sep=",", encoding="latin1")
gdf = gpd.read_file(caminho_geojson)

# === Normalização ===
df['area'] = df['area'].astype(str).str.upper().str.strip()
df['parametro'] = df['parametro'].astype(str).str.strip()
df['tipo_da_forma_de_abastecimento'] = df['tipo_da_forma_de_abastecimento'].astype(str).str.strip()
df['resultado'] = df['resultado'].astype(str).str.strip()
gdf['nome_bairr'] = gdf['nome_bairr'].astype(str).str.upper().str.strip()

# === Parâmetros desejados ===
parametros_alvo = [
    'Escherichia coli',
    'Turbidez (uT)',
    'Cloro residual livre (mg/L)',
    'Coliformes totais'
]

# === Filtra somente os parâmetros desejados ===
df_parametros = df[df['parametro'].isin(parametros_alvo)]

# === Pega o último resultado de cada parâmetro por bairro ===
df_parametros = df_parametros.sort_values(by='data_da_coleta')
df_pivot = df_parametros.pivot_table(
    index='area',
    columns='parametro',
    values='resultado',
    aggfunc='last'
).reset_index()

# === Pega forma de abastecimento mais recente por bairro ===
forma_abastecimento = df.sort_values(by='data_da_coleta').drop_duplicates(subset='area', keep='last')[['area', 'tipo_da_forma_de_abastecimento']]
forma_abastecimento.columns = ['nome_bairr', 'forma_abastecimento']

# === Junta tudo ===
df_pivot.columns.name = None
df_pivot.rename(columns={'area': 'nome_bairr'}, inplace=True)
dados = df_pivot.merge(forma_abastecimento, on='nome_bairr', how='left')

# === Merge com GeoDataFrame ===
gdf_merged = gdf.merge(dados, on='nome_bairr', how='left')

# === Função de estilo ===
def estilo_bairro(feature):
    props = feature['properties']
    sem_dados = all(pd.isna(props.get(p)) for p in parametros_alvo)

    if sem_dados:
        return {
            'fillColor': 'gray',
            'color': 'black',
            'weight': 0.5,
            'fillOpacity': 0.5
        }

    # Validação dos parâmetros
    try:
        cloro = float(str(props.get('Cloro residual livre (mg/L)')).replace(',', '.'))
        cloro_ok = 0.2 <= cloro <= 5.0
    except:
        cloro_ok = False

    try:
        turbidez = float(str(props.get('Turbidez (uT)')).replace(',', '.'))
        turbidez_ok = turbidez <= 5.0
    except:
        turbidez_ok = False

    ecoli = str(props.get('Escherichia coli')).strip().upper()
    ecoli_ok = ecoli == 'AUSENTE'

    coliformes = str(props.get('Coliformes totais')).strip().upper()
    coliformes_ok = coliformes == 'AUSENTE'

    dentro_do_padrao = all([cloro_ok, turbidez_ok, ecoli_ok, coliformes_ok])
    return {
        'fillColor': 'green' if dentro_do_padrao else '#e57373',
        'color': 'black',
        'weight': 0.4,
        'fillOpacity': 0.6
    }

# === Cria o mapa ===
mapa = folium.Map(location=[-12.97, -38.50], zoom_start=11, tiles='CartoDB positron')

# === Embed do Google Form ===
google_form_iframe = """
    <iframe src="https://docs.google.com/forms/d/e/1FAIpQLSeB2emqWnkhaOmYcr1n-A2gu7H-DK6fciY0Kn7_qmlOwCUD2A/viewform?usp=header" width="640" height="844" frameborder="0" marginheight="0" marginwidth="0">Carregando…</iframe>
"""

# === Função para adicionar o formulário no popup ===
iframe = IFrame(google_form_iframe, width=650, height=900)
popup = folium.Popup(iframe, max_width=1000)

# Adiciona um marcador com o formulário de denúncia
folium.Marker(
    location=[-12.97, -38.50],  # Localização central para exemplo
    popup=popup,
    icon=folium.Icon(color='blue', icon='info-sign')
).add_to(mapa)

# === Adiciona os bairros com o GeoJson ===
folium.GeoJson(
    gdf_merged,
    style_function=estilo_bairro,
    tooltip=GeoJsonTooltip(
        fields=['nome_bairr', 'forma_abastecimento'] + parametros_alvo,
        aliases=['Bairro:', 'Forma de abastecimento:'] + [f'{p}:' for p in parametros_alvo],
        localize=True
    ),
    name='Dados por bairro'
).add_to(mapa)

folium.LayerControl().add_to(mapa)

# === Salva o mapa ===
mapa.save(saida_html)
print(f"✅ Mapa salvo com sucesso em: {saida_html}")