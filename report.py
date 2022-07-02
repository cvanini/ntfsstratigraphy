### sources : https://dash.plotly.com/, https://predict-idlab.github.io/plotly-resampler/getting_started.html

from dash import Dash, dcc, html, dash_table, Input, Output
import io
import plotly.express as px
from base64 import b64encode
from parser.boot import *
from parser.bitmap import *
from data_processing import *
from plotly_resampler import FigureResampler
from argparse import ArgumentParser
from datetime import datetime

# pio.templates.default = "none"
logger = logging.getLogger('parser')

if __name__ == "__main__":
    parser = ArgumentParser(description='')
    parser.add_argument('-f', '--file', help='MFT_file', required=True)
    parser.add_argument('-b', '--boot-file', help='Boot_file', required=True)

    args = parser.parse_args()

    # Data
    # ------------------------------------------------------------------------------------------------------------------
    df = open_(args.file)
    df = pre_processing(df)
    df = flag_system_files(df)
    boot_info = parse_boot(args.boot_file)
    boot_info = [{'Information': k, 'Valeur': v} for k, v in boot_info.items()]
    columns = ['SI creation time', 'SI modification time', 'SI last accessed time', 'SI entry modification time',
               'FN creation time', 'FN modification time', 'FN last accessed time', 'FN entry modification time']
    #free_spaces = test_algorithm(bitmap)

    # App layout
    # ------------------------------------------------------------------------------------------------------------------
    app = Dash(__name__)
    app.title = "Stratigraphy analysis report"
    buffer = io.StringIO()
    colorscales = px.colors.named_colorscales()

    style = {'font-family': 'sans-serif', 'text-align': 'left', 'color': '#006080', 'margin-left': '10px'}

    html_bytes = buffer.getvalue().encode()
    encoded = b64encode(html_bytes).decode()
    #
    app.layout = html.Div(children=[
        html.Div([
            html.Div([
                html.H1("Stratigraphy analysis report", style=style),
            ]),
        ], style={'background-color': '#e6f2ff', 'margin-top': '-38px', 'width': '100%', 'margin-left': '-38px',
                  'height': '60px', 'padding': '30px', 'display': 'flex', 'border': '1px solid lightblue'}),
        html.Div([
            html.Div([
                html.H3("Volume information extracted from the $boot file: ",
                        style={'color': '#0086b3', 'font-family': 'sans-serif', 'font-weight': 'bold', 'margin-top': '0px'}),
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
                html.P("", style={'margin-bottom': '1cm'}),
                html.H3("Visualization : ",
                        style={'color': '#0086b3', 'font-family': 'sans-serif', 'font-weight': 'bold'}),
                html.Div([
                    html.P("some random text to present the graph"),
                    html.P("", style={'margin-bottom': '1cm'}),
                ]),
                html.Div([
                    html.P("Choose the time type :",
                           style={"text-align": "left"}),
                    dcc.Dropdown(
                        id='y_axis',
                        options=[{"value": x, "label": x} for x in df.columns if x in columns],
                        clearable=False,
                        style={"width": "60%"},
                    ),
                ], style={'margin-left': '30px'}),
                html.P("", style={'margin-bottom': '1cm'}),
                html.H3("Results : ",
                        style={'color': '#0086b3', 'font-family': 'sans-serif', 'font-weight': 'bold'}),
                html.Div([
                    html.P("Possible deletion at.."),
                    html.P("", style={'margin-bottom': '1cm'}),
                ]),
            ]),
            html.Div([
                html.Div([
                    html.H4(f"datetime of analysis :   "),
                ]),
                html.Div([
                    html.P(f"{datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"),
                ], style={'margin-top': '6px', 'margin-left': '10px'}),
            ], style={'margin-left': '500px', 'display': 'flex'}),
        ], style={'font-family': 'sans-serif', 'margin-left': '5px', 'display': 'flex', 'margin-top': '20px', 'width': '100%'}),
        dcc.Graph(id="scatter-plot"),
        html.P("Note : you can download the graph as a PNG", style={"text-align": "left", 'font-family': 'sans-serif'}),
        html.A(
            html.Button("bloup"),
            id="interactive-html-export-x-download",
            href="data:text/html;base64," + encoded,
            download="plotly_graph.html"
        ),
    ])



    # fig2.register_update_graph_callback(
    #     parser=parser, graph_id="graph-id", trace_updater_id="trace-updater"
    # )

    #
    # @parser.callback(
    #     Output("graph-id", "figure"),
    #     [Input("dropdown", "value")])
    # def change_colorscale(scale):
    #
    #     fig2 = px.scatter(
    #         df, x="Entry number", y="SI creation time",
    #         color="LSN", color_continuous_scale=scale)
    #     return fig2

    # @parser.callback(
    #     Output("MFT_time", "figure"),
    #     [Input("y_axis", "value")],
    # )
    # def update_graph(y_axis):
    #     if not y_axis:
    #         raise Exception
    #     fig = FigureResampler(px.scatter(
    #         df, x="Entry number", y=y_axis, color='Usage',
    #         color_discrete_map={'System': '#CBCBCB', 'Other': 'Gray', 'MFT': 'red', 'User': '#008aba'},
    #         render_mode='webgl',
    #         title=f'MFT entry / {y_axis}'))
    #     # marker_line=dict(width=1,)
    #     fig.update_traces(marker=dict(size=5, ))
    #
    #     return [fig]

    app.run_server(debug=True, dev_tools_hot_reload=True)
