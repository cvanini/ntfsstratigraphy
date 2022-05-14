from parser.boot import *
from data_processing import *
from datetime import datetime
from callback import *
import dash_bootstrap_components as dbc
from dash import Dash, dcc, html, dash_table

app = Dash(__name__, external_stylesheets=[dbc.themes.SANDSTONE])
app.title = "Stratigraphy analysis report"

# Data
# ----------------------------------------------------------------------------------------------------------------------
today = datetime.now()
df = open_("./parser/outputs/CT.csv")
df = pre_processing(df)
df = flag_system_files(df)

boot_info = parse_boot("./parser/data/CT/$Boot")
boot_info = [{'Information': k, 'Valeur': v} for k, v in boot_info.items()]
columns = ['SI creation time', 'SI modification time', 'SI last accessed time', 'SI entry modification time',
           'FN creation time', 'FN modification time', 'FN last accessed time', 'FN entry modification time']

# App layout
# ----------------------------------------------------------------------------------------------------------------------
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H1("Stratigraphy analysis report"),
                className='text-left text-primary, mb-4')
    ]),
    dbc.Row([
        dbc.Col(
            dash_table.DataTable(
                    id='boot',
                    columns=(
                            [{'id': 'Information', 'name': 'Information'}] +
                            [{'id': 'Valeur', 'name': 'Valeur'}]
                    ),
                    data=boot_info,
                    editable=False,
                    style_header={
                        'font-family': 'sans-serif',
                        'fontWeight': 'bold',
                        'border': '1px solid black',
                    },
                    style_cell={'textAlign': 'left'},
                    style_data={
                        'whiteSpace': 'normal',
                        'height': 'auto',
                        'lineHeight': '10px',
                        'font-family': 'sans-serif',
                    },
                    style_table={'width': '600px', 'marginLeft': '50px'},
                ),
        ),
        dbc.Col(html.Div([
            html.P("Choose the time type :",
                   style={"text-align": "left"}),
            dcc.Dropdown(
                id='y_axis',
                options=[{"value": x, "label": x} for x in df.columns if x in columns],
                clearable=False,
                style={"width": "60%"},
            ),
            #dcc.Graph(id="scatter-plot"),
        ]),
        )
    ])
])


if __name__ == '__main__':
    app.run_server(debug=True)
