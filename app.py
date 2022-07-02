from parser.boot import *
from pathlib import Path
from data_processing import *
from datetime import datetime
from plotly_resampler import FigureResampler
import plotly.express as px
import dash_bootstrap_components as dbc
from dash import Dash, dcc, html, dash_table, Input, Output

app = Dash(__name__, external_stylesheets=[dbc.themes.SANDSTONE], suppress_callback_exceptions=True)
app.title = "Stratigraphy analysis report"

# Data
# ----------------------------------------------------------------------------------------------------------------------
today = datetime.now()
# file = ".\parser\outputs\BLANC_ORDI\MFT.csv"
# file = ".\\parser\\data\\Christopher\\MFT.csv"
# file = "C:\\Users\\celin\\UNIVERSITÉ\\MA2S2\\Travail de Master\\Results\\11042022_1\\1617\\MFT.csv"
file = "C:\\Users\\celin\\UNIVERSITÉ\\MA2S2\\Travail de Master\\Results\\22042022_4\\1667\\MFT.csv"
df = open_(Path(file))
df = pre_processing(df)
OS = check_OS(df)
df = flag_system_files(df)
text, df = recycle_bin(df)
df = deletion(df)
# df2 = df[df['Events'].notna()]

boot_info = parse_boot(Path("C:\\Users\\celin\\UNIVERSITÉ\\MA2S2\\Travail de Master\\Results\\11042022_1\\0\\$Boot"))
# boot_info = parse_boot(".\parser\outputs\BLANC_ORDI\$Boot")
boot_info = [{'Information': k, 'Value': v} for k, v in boot_info.items()]
columns = ['SI creation time', 'SI modification time', 'SI last accessed time', 'SI entry modification time',
           'FN creation time', 'FN modification time', 'FN last accessed time', 'FN entry modification time']
columns_color = ['Allocation flag (verbose)', 'Usage']

try:
    boot_info.append({'Information': 'Volume name', 'Value': df.loc[3, 'Volume name']})
    boot_info.append({'Information': 'NTFS version', 'Value': df.loc[3, 'NTFS version']})
except KeyError:
    pass

# graphs
# ----------------------------------------------------------------------------------------------------------------------
MFT_cluster = FigureResampler(px.scatter(
    df.sort_values(by='First cluster (all)'),
    x="First cluster (all)",
    y="Entry number",
    height=600,
    width=900,
    color='Stratum',
    color_discrete_map={
        '0': '#C0C0C0',
        '1': '#008ccc',
        '2': 'red',
        # '3': 'pink',
    },
    opacity=0.8,
    title=f'MFT entry number / First cluster',
    labels=dict(x='First cluster', y='MFT entry number'),
    custom_data=['Filename', 'SI creation time']
))

MFT_cluster.update_traces(
    marker={'size': 3, },
    hovertemplate="<br>".join([
        "<b>%{customdata[0]}</b>",
        "First cluster: %{x}",
        "Entry number: %{y}",
        "Creation time: %{customdata[1]}"
    ]))

MFT_cluster.update_layout(
    plot_bgcolor='white',
    hovermode="x",
    hoverlabel=dict(bgcolor='white', ),
    font=dict(color='#072f5f', ),
    yaxis_tickformat='d',
    xaxis_tickformat='d',
)
# # marker_line_width=0.5
MFT_cluster.update_xaxes(
    title_font_color='#072f5f',
    color='black',
    linecolor='black',
    gridcolor='#ECEFF1',
    mirror=False,
    showgrid=True,
    zeroline=False,
)
MFT_cluster.update_yaxes(
    title_font_color='#072f5f',
    color='black',
    linecolor='black',
    gridcolor='#ECEFF1',
    mirror=False,
    showgrid=True,
    zeroline=False,
    range=[-1, df['Entry number'].iloc[-1] + 10],
)


# First page
# ----------------------------------------------------------------------------------------------------------------------
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
                    style_table={'width': '600px', 'marginLeft': '30px'},
                ),
            ], className='mb-3 me-5, hstack gap-10'),
        ]),
        dbc.Col([
            html.Div([
                html.Div(['Report information'], className='card-header'),
                html.Div([
                    html.P([html.Strong(f"Report generated on : "), f"{datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"],
                           className='card-title'),
                    html.P([html.Strong(f"File: "), f"{file}"], className='card-title')
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
            html.P(children=['The operating system was installed on : ',
                             html.Strong(f"{(df.loc[0, 'SI creation time']).strftime('%d.%m.%Y %H:%M:%S')}")] if OS == True else '',
                   className='mb-1', style={'margin-left': '30px'}),
            html.P(children=['The root directory creation timestamp is : ',
                             html.Strong(f"{(df.loc[5, 'SI creation time']).strftime('%d.%m.%Y %H:%M:%S')}")],
                   className='mb-1', style={'margin-left': '30px'}),
        ], className='mb-4'),
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
        dbc.Col(
            html.Div([
                html.Strong("Choose the filtering color :", className='text-primary',
                            style={'text-align': 'left', 'margin-top': '10px'}),
                dcc.Dropdown(
                    id='color',
                    options=[{"value": x, "label": x} for x in df.columns if x in columns_color],
                    clearable=False,
                    style={"width": "40%"},
                ),
            ]),
        ),
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
            #dcc.Graph(figure=MFT_cluster)
        ], style={'marginLeft': '40px'}),
    ]),
])

# Third page
# ----------------------------------------------------------------------------------------------------------------------
layout3 = dbc.Container([
dbc.Row([
        dbc.Col([
            html.H5([html.Strong('Sequence of events: ')], className='text-primary'),
            html.P('The following sequence of events was extracted from the analysis of the $MFT :',
                   className='text-primary'),
            html.Div(children=[html.P(
                [f'[{x[0][:-1]}]\n the file ', html.Strong(x[1]), f' (entry {x[2]}) was moved to the $RECYCLE.BIN']) for
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


@app.callback(
    Output("scatter-plot", "figure"),
    Input("y_axis", "value"))
def update_scatter(column):
    # df.loc[df['SI creation time'] == '', 'Stratum'] = ''
    fig = FigureResampler(px.scatter(
        df,
        x="Entry number",
        y=column,
        height=500,
        width=1300,
        color='Stratum',
        color_discrete_map={
            '0': '#C0C0C0',
            '1': '#008ccc',
            '2': 'red', #99dfff
            '3': '#008ccc'
        },
        # color='Allocation flag (verbose)',
        # color_discrete_map={'Visible file': '#3895d3', 'Visible directory': '#29a3a3', 'Deleted file': '#ff9999',
        #                     'Deleted directory': '#ff1a66'},
        opacity=0.8,
        title=f'{column} / MFT entry number',
        labels=dict(x='MFT entry number', y=column),
        custom_data=['Filename']
    ))

    fig.update_traces(
        marker=dict(size=3,),
        hovertemplate="<br>".join([
            "<b>%{customdata[0]}</b>",
            "Timestamp: %{y}",
            "Entry number: %{x}",
        ])
    )

    fig.update_layout(
        plot_bgcolor='white',
        hovermode="x",
        hoverlabel=dict(bgcolor='white', font_size=12),
        font=dict(color='#072f5f', ),
        yaxis_tickformat='%d.%m.%Y %H:%M:%S',
        xaxis_tickformat='d',
    )
    # # marker_line_width=0.5
    fig.update_xaxes(
        title_font_color='#072f5f',
        color='black',
        linecolor='black',
        gridcolor='#ECEFF1',
        mirror=False,
        showgrid=True,
        zeroline=False,
        # range=[-1, len(df) + 1]
    )
    fig.update_yaxes(
        title_font_color='#072f5f',
        color='black',
        linecolor='black',
        gridcolor='#ECEFF1',
        mirror=False,
        showgrid=True,
        zeroline=False
    )

    return fig



@app.callback(
    Output("scatter-plot_", "figure"),
    Input("y_axis_", "value"))
def update_scatter(column):
    # df.loc[df['SI creation time'] == '', 'Stratum'] = ''
    fig = FigureResampler(px.scatter(
        df.sort_values(by='First cluster (all)'),
        x="First cluster (all)",
        y=column,
        height=500,
        width=1300,
        color='Stratum',
        color_discrete_map={
            '0': '#C0C0C0',
            '1': '#008ccc',
            '2': 'red',
        },
        # color='Allocation flag (verbose)',
        # color_discrete_map={'Visible file': '#3895d3', 'Visible directory': '#29a3a3', 'Deleted file': '#ff9999',
        #                     'Deleted directory': '#ff1a66'},
        opacity=0.8,
        title=f'{column} / First cluster',
        labels=dict(x='First cluster', y=column),
        custom_data=['Filename']
    ))

    fig.update_traces(
        marker={'size': 3, },
        hovertemplate="<br>".join([
            "<b>%{customdata[0]}</b>",
            "First cluster: %{x}",
            "Timestamp: %{y}",
        ])
    )

    fig.update_layout(
        plot_bgcolor='white',
        hovermode="x",
        hoverlabel=dict(bgcolor='white', font_size=12),
        font=dict(color='#072f5f', ),
        yaxis_tickformat='%H:%M:%S',
        xaxis_tickformat='d',
    )
    # # marker_line_width=0.5
    fig.update_xaxes(
        title_font_color='#072f5f',
        color='black',
        linecolor='black',
        gridcolor='#ECEFF1',
        mirror=False,
        showgrid=True,
        zeroline=False,
        # range=[-1, len(df) + 1]
    )
    fig.update_yaxes(
        title_font_color='#072f5f',
        color='black',
        linecolor='black',
        gridcolor='#ECEFF1',
        mirror=False,
        showgrid=True,
        zeroline=False
    )

    return fig


if __name__ == '__main__':
    app.run_server(debug=True)
