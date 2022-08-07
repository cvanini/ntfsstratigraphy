'''
Céline Vanini
07. 2022
'''

from rules import *
from parser.boot import *
from pathlib import Path
from datetime import datetime
from plotly_resampler import FigureResampler
import plotly.express as px
import dash_bootstrap_components as dbc
from dash import Dash, dcc, html, dash_table, Input, Output

########################################################################################################################

app = Dash(__name__, external_stylesheets=[dbc.themes.SANDSTONE], suppress_callback_exceptions=True)
app.title = "Stratigraphy analysis report"
logger = logging.getLogger('app')
today = datetime.now()

columns = ['SI creation time', 'SI modification time', 'SI entry modification time', 'SI last accessed time',
           'FN creation time', 'FN modification time', 'FN entry modification time', 'FN last accessed time']

########################################################################################################################


parser = ArgumentParser(description='bloup')

parser.add_argument('-d', '--directory', help='Path to the directory containing the MFT and Boot files in CSV format')
parser.add_argument('-o', '--output', help='bloup')
args = parser.parse_args()

if not os.path.isdir(args.output):
    os.mkdir(args.output)

logging.basicConfig(format='%(asctime)s - %(name)-12s: %(message)s',
                    datefmt='[%d.%m.%Y %H:%M:%S]', level=logging.INFO,
                    handlers=[logging.FileHandler(f'{args.output}\\report.txt'), logging.StreamHandler()])

logger.info('Starting the analysis')

# boot_info = [{'Information': k, 'Value': v} for k, v in boot_info.items()]
#
# try:
#     boot_info.append({'Information': 'Volume name', 'Value': df.loc[3, 'Volume name']})
#     boot_info.append({'Information': 'NTFS version', 'Value': df.loc[3, 'NTFS version']})
# except KeyError:
#     pass

####################################################################################################################
# DATA

dir = Path(args.directory)
if dir.is_dir():
    # opening the boot.csv as a panda dataframe
    df_boot = open_boot_file(dir)
    # opening the MFT.csv as a panda dataframe
    df = open_MFT_file(dir)
    df = pre_processing(df)
    # adding some useful information to the boot dataframe
    df_boot = boot_app(df_boot, df)
    # check is there is an OS installed
    OS = check_OS(df)

    # testing rules
    text, df = recycle_bin(df)


else:
    raise Exception(f"The directory doesn't exists: {dir}")

# file = ".\parser\outputs\BLANC_ORDI\MFT.csv"
# file = "C:\\Users\\celin\\UNIVERSITE\\MA2S2\\TdM\\Results\\09072022_4\\799\\MFT.csv"
# file = "C:\\Users\\celin\\UNIVERSITÉ\\MA2S2\\Travail de Master\\Results\\11042022_1\\1617\\MFT.csv"
# file = "C:\\Users\\celin\\UNIVERSITE\\MA2S2\\TdM\\Results\\BLANC_ORDI\\BLANC_ORDI\\MFT.csv"
# df = open_(Path(file))
# df = pre_processing(df)
# OS = check_OS(df)
# df = flag_system_files(df)
# df = deletion(df)
# df2 = df[df['Events'].notna()]

# graphs
####################################################################################################################

# First page
####################################################################################################################
layout1 = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H5([html.Strong('Volume information')], className='text-primary'),
            html.P('The following table contains information extracted from the $Boot file :',
                   className='text-primary'),
            html.Div([
                dash_table.DataTable(
                    id='boot',
                    columns=(
                            [{'id': 'Information', 'name': 'Information'}] +
                            [{'id': 'Value', 'name': 'Value'}]
                    ),
                    data=df_boot.to_dict('records'),
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
                    style_table={'width': '600px', 'marginLeft': '30px'},
                ),
            ], className='mb-3 me-5, hstack gap-10'),
        ]),
        dbc.Col([
            html.Div([
                html.Div(['Report information'], className='card-header'),
                html.Div([
                    html.P(
                        [html.Strong(f"Report generated on : "), f"{datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"],
                        className='card-title'),
                    html.P([html.Strong(f"File: "), f"{args.directory}\\MFT.csv"], className='card-title')
                ], className='card-body')
            ], className='card border-dark mb-4',
                style={"max-height": '30rem', "text-align": "left", 'margin-left': '200px'})
        ]),
    ]),
])

# Second page
# ----------------------------------------------------------------------------------------------------------------------
layout2 = dbc.Container([
    dbc.Row([
        dbc.Col(children=[
            html.H5([html.Strong('Analysis of the Master File Table')], className='text-primary'),
            html.P('Information extracted from the first entries :', className='text-primary'),
            html.P(children=['The MFT is at cluster : ', html.Strong(f"{int(df.loc[0, 'First cluster'])}")],
                   className='mb-1', style={'margin-left': '30px'}),
            html.P(children=['Number of entries in the MFT : ', html.Strong(f'{len(df)}')], className='mb-1',
                   style={'margin-left': '30px'}),
            html.P(children=["The number of cluster in the volume is (from $BadCluster' ADS run list): ",
                             html.Strong(f"{(df.loc[8, 'ADS Run list']).split(',')[1].split(')')[0]}")],
                   className='mb-1', style={'margin-left': '30px'}),
            # html.P(children=["The number of cluster in the volume is (from the $Boot file): ",
            #                  html.Strong(f"{(df.loc[8, 'ADS Run list']).split(',')[1].split(')')[0]}")],
            #        className='mb-1', style={'margin-left': '30px'}),
            html.P(children=['The operating system was installed on : ',
                             html.Strong(
                                 f"{(df.loc[0, 'SI creation time']).strftime('%d.%m.%Y %H:%M:%S')}")] if OS == True else '',
                   className='mb-1', style={'margin-left': '30px'}),
            html.P(children=['$MFT creation timestamp : ',
                             html.Strong(f"{(df.loc[0, 'SI creation time']).strftime('%d.%m.%Y %H:%M:%S')}")],
                   className='mb-1', style={'margin-left': '30px'}),
            html.P(children=['The root directory creation timestamp is : ',
                             html.Strong(f"{(df.loc[5, 'SI creation time']).strftime('%d.%m.%Y %H:%M:%S')}")],
                   className='mb-1', style={'margin-left': '30px'}),
        ], className='mb-4'),
        html.P('The following table contains information relating to the first 16 entries :',
               className='text-primary'),
        html.Div([
            dash_table.DataTable(
                id='first_entries',
                columns=(
                        [{'id': 'Entry number', 'name': 'Entry number'}] +
                        [{'id': 'Filename', 'name': 'Filename'}] +
                        [{'id': 'SI creation time', 'name': 'C (SI)'}] +
                        [{'id': 'SI modification time', 'name': 'M (SI)'}] +
                        [{'id': 'SI last accessed time', 'name': 'A (SI)'}] +
                        [{'id': 'SI entry modification time', 'name': 'E (SI)'}] +
                        [{'id': 'FN creation time', 'name': 'C (FN)'}] +
                        [{'id': 'FN modification time', 'name': 'M (FN)'}] +
                        [{'id': 'FN last accessed time', 'name': 'A (FN)'}] +
                        [{'id': 'FN entry modification time', 'name': 'E (FN)'}]
                ),
                data=df.iloc[:16].to_dict('records'),
                editable=False,
                fixed_columns={'headers': True, 'data': 2},
                style_header={
                    'font-family': 'sans-serif',
                    'fontWeight': 'bold',
                    'border': '1px solid black',
                },
                style_cell={
                    'textAlign': 'left',
                    'height': 'auto',
                    # all three widths are needed
                    'minWidth': '180px', 'width': '180px', 'maxWidth': '180px',
                    'whiteSpace': 'normal'
                },
                style_cell_conditional=[
                    {'if': {'column_id': 'Entry number'},
                     'width': '10%'},
                ],
                style_data={
                    'whiteSpace': 'normal',
                    'height': 'auto',
                    'lineHeight': '10px',
                    'font-family': 'sans-serif',
                    'font-size': '13px'
                },
                style_table={'marginLeft': '30px', 'overflowX': 'auto', 'minWidth': '100%'},
                # export_format="csv",
            ),
        ], className='mb-3 me-5'),
    ]),
    dbc.Row([
        dbc.Col(
            html.Div([
                html.Strong("Choose the y axis :", className='text-primary',
                            style={'text-align': 'left', 'margin-top': '10px'}),
                dcc.Dropdown(
                    id='y_axis',
                    options=[{"value": x, "label": x} for x in df.columns if x in columns],
                    clearable=False,
                    style={"width": "70%"},
                ),
            ]),
        ),
        # dbc.Col(
        #     html.Div([
        #         html.Strong("Choose the filtering color :", className='text-primary',
        #                     style={'text-align': 'left', 'margin-top': '10px'}),
        #         dcc.Dropdown(
        #             id='color',
        #             options=[{"value": x, "label": x} for x in df.columns if x in columns_color],
        #             clearable=False,
        #             style={"width": "40%"},
        #         ),
        #     ]),
        # ),
    ], style={'margin-top': '20px'}),
    dbc.Row([
        dcc.Graph(id="scatter-plot"),
    ], style={'marginLeft': '30px'}),
    dbc.Row([
        dbc.Col(
            html.Div([
                html.Strong("Choose the y axis :", className='text-primary',
                            style={'text-align': 'left', 'margin-top': '10px'}),
                dcc.Dropdown(
                    id='y_axis_',
                    options=[{"value": x, "label": x} for x in df.columns if x in columns],
                    clearable=False,
                    style={"width": "70%"},
                ),
            ]),
        ),
    ], style={'margin-top': '20px'}),
    dbc.Row([
        dcc.Graph(id="scatter-plot_"),
    ], style={'marginLeft': '30px', 'max-width': '500px', 'height': '500px'}),
    dbc.Row([
        dbc.Col([
            html.P(
                'Note : stratum are based on the sequence number of each file. The files with strata 0 are system files created during the first formatting of the volume'),
        ], style={'marginLeft': '40px'}),
    ]),
])

# Third page
# ------------------------------------------------------------------------------------------------------------------
layout3 = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H5([html.Strong('Sequence of events: ')], className='text-primary'),
            html.P('The following sequence of events was extracted from the analysis of the $MFT :',
                   className='text-primary'),
            html.Div(children=[html.P(
                [f'[{x[0][:-1]}]\n the file ', html.Strong(x[1]), f' (entry {x[2]}) was moved to the $RECYCLE.BIN'])
                for
                x in text], style={'marginLeft': '30px'})
            # , corresponding $I: {x[3]} (entry {x[4]})
        ], className='mb-4'),
    ], className='mb-4'),
    dbc.Row([
        dbc.Col([
            html.Div([
                html.Div(['Notes'], className='card-header'),
                html.Div([
                    html.P(['There is no file in the $RECYCLE.BIN' if text == '' else ''], className='card-title'),
                ], className='card-body')
            ], className='card border-dark mb-4',
                style={"max-height": '30rem', "text-align": "left", 'max-width': '300px'}),
        ])
    ])
])

# Fourth page
# ----------------------------------------------------------------------------------------------------------------------
layout4 = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H4([html.Strong('NTFS stratigraphy analysis')], className='text-primary'),
            html.P(
                'Stratigraphy analysis on a volume formatted with NTFS takes advantages of various information extracted from the $MFT file: '),
            html.Div([
                html.P([html.Strong('Entry number: '), ''], className='mb-2'),
                html.P([html.Strong('Sequence number: '), ''], className='mb-2'),
                html.P([html.Strong('LogFile Sequence Number (LSN): '), ''], className='mb-2'),
                html.P([html.Strong('Parent entry number: '), ''], className='mb-2'),
                html.P([html.Strong('$STANDARD_INFORMATION attribute timestamps: '), ''], className='mb-2'),
                html.P([html.Strong('$FILE_NAME attribute timestamps: '), ''], className='mb-2'),
                html.P([html.Strong('Path: '), ''], className='mb-2'),
                html.P([html.Strong('Allocation flag: '), ''], className='mb-2'),
                html.P([html.Strong('Base record reference: '), ''], className='mb-2'),
            ], style={'margin-left': '30px'}),
        ]),
    ], className='mb-4'),
    dbc.Row([
        dbc.Col(children=[
            html.H5([html.Strong('File creation')], className='text-primary'),
            html.P(
                'File creation on a volume formatted with NTFS is inherently dependent of the allocation algorithms. MFT entries are allocated following a first fit strategy and clusters are allocated following a best fit strategy, rendering the analysis by stratigraphy more challenging.'),
        ], className='mb-4'),
    ], className='me-5'),
    dbc.Row([
        dbc.Col([
            html.Div([
                html.Div([html.Strong('Observations in the Master File Table')], className='card-header'),
                html.Div([
                    html.P([html.Strong('First fit : '), 'bloup'], className='card-title'),
                    html.P([html.Strong('Best fit : '), 'bloup'], className='card-title'),
                ], className='card-body')
            ], className='card border-dark mb-4',
                style={"max-height": '30rem', "text-align": "left", 'max-width': '600px'}),
        ], style={'margin-left': '30px'}),
        dbc.Col([
            html.Div([
                html.Div([html.Strong('Observations in the clusters')], className='card-header'),
                html.Div([
                    html.P([html.Strong('First fit : '), 'bloup'], className='card-title'),
                    html.P([html.Strong('Best fit : '), 'bloup'], className='card-title'),
                ], className='card-body')
            ], className='card border-dark mb-4',
                style={"max-height": '30rem', "text-align": "left", 'max-width': '600px'}),
        ], style={'margin-left': '100px'}),
        dbc.Row([
            dbc.Col(children=[
                html.H5([html.Strong('File moved to the $RECYCLE.BIN')], className='text-primary'),
                html.P(
                    'When a file is moved to the $RECYCLE.BIN for the first time on a volume, the $RECYCLE.BIN directory and sub-directories are created and allocated on the volume.'),
                html.P('Filenames are replaced by a 6-random character string beginning with $R',
                       style={'margin-left': '30px'}),
                html.P('$I files associated to $R files are created',
                       style={'margin-left': '30px'}),

            ], className='mb-4, mt-4'),
        ], className='mb-3 me-5, hstack gap-10'),
        # dbc.Col([
        #     html.Div([
        #         html.Div(['Allocation strategies'], className='card-header'),
        #         html.Div([
        #             html.P([html.Strong('First fit : '), 'bloup'], className='card-title'),
        #             html.P([html.Strong('Best fit : '), 'bloup'], className='card-title'),
        #         ], className='card-body')
        #     ], className='card border-dark mb-4', style={"max-height": '30rem', "text-align": "left", 'max-width': '300px'}),
        # ], style={'margin-left': '300px'}),
    ]),
    dbc.Row([
        dbc.Col([
            html.Div([
                dbc.Accordion([
                    dbc.AccordionItem('hello', title='File creation'),
                    dbc.AccordionItem('hello', title='File deletion'),
                    dbc.AccordionItem('hello', title='File moved to the $RECYCLE.BIN'),
                    dbc.AccordionItem('hello', title='Backdating'),
                    dbc.AccordionItem('hello', title='System time change'),
                    dbc.AccordionItem('hello', title='Formatting'),
                    dbc.AccordionItem('hello', title='Operating system restoration'),
                ], start_collapsed=True, always_open=True)
            ]),
        ])
    ]),
    #     dbc.Row([
    #         dbc.Col([
    #             html.Div([
    #                 html.P('Entries are allocated following the first fit strategy'),
    #                 html.P('Entries numbers are assigned incrementially'),
    #                 html.P(''),
    #                 html.P(''),
    #             ], style={'margin-left': '30px'}),
    #             html.Strong('Observations in the cluster: '),
    #         ]),
    #     ]),
    #     dbc.Row([
    #         dbc.Col(children=[
    #             html.H5([html.Strong('File deletion')], className='text-primary'),
    #             html.P('Information extracted from the first entries :', className='text-primary'),
    #             html.P(''),
    #         ], className='mb-4, mt-4'),
    #     ], className='mb-3 me-5, hstack gap-10'),

    #     dbc.Row([
    #         dbc.Col(children=[
    #             html.H5([html.Strong('Backdating')], className='text-primary'),
    #             html.P('Information extracted from the first entries :', className='text-primary'),
    #             html.P(''),
    #         ], className='mb-4, mt-4'),
    #     ], className='mb-3 me-5, hstack gap-10'),
    #     dbc.Row([
    #         dbc.Col(children=[
    #             html.H5([html.Strong('System time change')], className='text-primary'),
    #             html.P('Information extracted from the first entries :', className='text-primary'),
    #             html.P(''),
    #         ], className='mb-4, mt-4'),
    #     ], className='mb-3 me-5, hstack gap-10'),
    #     dbc.Row([
    #         dbc.Col(children=[
    #             html.H5([html.Strong('Formatting')], className='text-primary'),
    #             html.P('Information extracted from the first entries :', className='text-primary'),
    #             html.P(''),
    #         ], className='mb-4, mt-4'),
    #     ], className='mb-3 me-5, hstack gap-10'),
    #     dbc.Row([
    #         dbc.Col(children=[
    #             html.H5([html.Strong('Operating system restoration')], className='text-primary'),
    #             html.P('Information extracted from the first entries :', className='text-primary'),
    #             html.P(''),
    #         ], className='mb-4, mt-4'),
    #     ], className='mb-3 me-5, hstack gap-10'),
])
# App layout
# ----------------------------------------------------------------------------------------------------------------------
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("Stratigraphy analysis report")],
            className='text-left text-primary, mb-4',
            style={'margin-top': '30px',
                   'height': '110px',
                   'background-color': '#e6f2ff',
                   'display': 'flex',
                   'padding': '20px',
                   'border': '2px solid lightblue'})
    ]),
    dbc.Row([
        dbc.Col([
            html.Div([
                dcc.Location(id="url"),
                html.Hr(),
                dbc.Nav([
                    dbc.NavLink("Volume information", href='/', active='exact'),
                    dbc.NavLink("Analysis", href='/page-1', active='exact'),
                    dbc.NavLink("Events", href='/page-2', active='exact'),
                    dbc.NavLink("Stratigraphy rules", href='/page-3', active='exact'),
                    dbc.NavLink("Entries information", href='/page-4', active='exact'),
                ], pills=True),
            ], style={"background-color": "#E9E9E9", 'display': 'flex'}),
        ], className='mb-4'),
    ]),
    dbc.Row([
        html.Div(id="page-content")
    ])
])


@app.callback(
    Output("page-content", "children"),
    [Input("url", "pathname")]
)
def display_page(pathname):
    if pathname == '/':
        return layout1
    elif pathname == '/page-1':
        return layout2
    elif pathname == '/page-2':
        return layout3
    elif pathname == '/page-3':
        return layout4
    elif pathname == '/page-4':
        return html.P("To be here soon..")
    return dbc.Jumbotron(
        [
            html.H1("404: Not found", className="text-danger"),
            html.Hr(),
            html.P(f"The pathname {pathname} was not recognised..."),
        ]
    )


# @app.callback(
#     Output("scatter-plot", "figure"),
#     Input("y_axis", "value"))
# def update_scatter(column):
#     # df.loc[df['SI creation time'] == '', 'Stratum'] = ''
#     fig = FigureResampler(px.scatter(
#         df,
#         x="Entry number",
#         y=column,
#         height=500,
#         width=1300,
#         color='Stratum',
#         color_discrete_map={
#             '0': '#C0C0C0',
#             '1': '#008ccc',
#             '2': 'red',  # 99dfff
#             '3': '#008ccc'
#         },
#         # color='Allocation flag (verbose)',
#         # color_discrete_map={'Visible file': '#3895d3', 'Visible directory': '#29a3a3', 'Deleted file': '#ff9999',
#         #                     'Deleted directory': '#ff1a66'},
#         opacity=0.8,
#         title=f'{column} / MFT entry number',
#         labels=dict(x='MFT entry number', y=column),
#         custom_data=['Filename']
#     ))
#
#     fig.update_traces(
#         marker=dict(size=3, ),
#         hovertemplate="<br>".join([
#             "<b>%{customdata[0]}</b>",
#             "Timestamp: %{y}",
#             "Entry number: %{x}",
#         ])
#     )
#
#     fig.update_layout(
#         plot_bgcolor='white',
#         hovermode="x",
#         hoverlabel=dict(bgcolor='white', font_size=12),
#         font=dict(color='#072f5f', ),
#         yaxis_tickformat='%d.%m.%Y %H:%M:%S',
#         xaxis_tickformat='d',
#     )
#     # # marker_line_width=0.5
#     fig.update_xaxes(
#         title_font_color='#072f5f',
#         color='black',
#         linecolor='black',
#         gridcolor='#ECEFF1',
#         mirror=False,
#         showgrid=True,
#         zeroline=False,
#         # range=[-1, len(df) + 1]
#     )
#     fig.update_yaxes(
#         title_font_color='#072f5f',
#         color='black',
#         linecolor='black',
#         gridcolor='#ECEFF1',
#         mirror=False,
#         showgrid=True,
#         zeroline=False
#     )
#
#     return fig


# @app.callback(
#     Output("scatter-plot_", "figure"),
#     Input("y_axis_", "value"))
# def update_scatter(column):
#     # df.loc[df['SI creation time'] == '', 'Stratum'] = ''
#     fig = FigureResampler(px.scatter(
#         df.sort_values(by='First cluster (all)'),
#         x="First cluster (all)",
#         y=column,
#         height=500,
#         width=1300,
#         color='Stratum',
#         color_discrete_map={
#             '0': '#C0C0C0',
#             '1': '#008ccc',
#             '2': 'red',
#         },
#         # color='Allocation flag (verbose)',
#         # color_discrete_map={'Visible file': '#3895d3', 'Visible directory': '#29a3a3', 'Deleted file': '#ff9999',
#         #                     'Deleted directory': '#ff1a66'},
#         opacity=0.8,
#         title=f'{column} / First cluster',
#         labels=dict(x='First cluster', y=column),
#         custom_data=['Filename']
#     ))
#
#     fig.update_traces(
#         marker={'size': 3, },
#         hovertemplate="<br>".join([
#             "<b>%{customdata[0]}</b>",
#             "First cluster: %{x}",
#             "Timestamp: %{y}",
#         ])
#     )
#
#     fig.update_layout(
#         plot_bgcolor='white',
#         hovermode="x",
#         hoverlabel=dict(bgcolor='white', font_size=12),
#         font=dict(color='#072f5f', ),
#         yaxis_tickformat='%H:%M:%S',
#         xaxis_tickformat='d',
#     )
#     # # marker_line_width=0.5
#     fig.update_xaxes(
#         title_font_color='#072f5f',
#         color='black',
#         linecolor='black',
#         gridcolor='#ECEFF1',
#         mirror=False,
#         showgrid=True,
#         zeroline=False,
#         # range=[-1, len(df) + 1]
#     )
#     fig.update_yaxes(
#         title_font_color='#072f5f',
#         color='black',
#         linecolor='black',
#         gridcolor='#ECEFF1',
#         mirror=False,
#         showgrid=True,
#         zeroline=False
#     )
#
#     return fig


if __name__ == '__main__':
    # launching the app
    app.run_server(debug=True)
