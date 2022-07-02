from plotly_resampler import FigureResampler
from dash import Dash, dcc, html, dash_table, Input, Output
import plotly.express as px
from plotly_resampler import FigureResampler
from app import *



@app.callback(
    Output("scatter-plot", "figure"),
    Input("y_axis", "value"))
def update_scatter(column):
    fig = FigureResampler(px.scatter(
        df, x="Entry number", y=column, color='Usage',
        color_discrete_map={'System': '#CBCBCB', 'Other': 'Gray', 'MFT': 'red', 'User': '#008aba'},
        render_mode='webgl', hover_data=['Filename'],
        title=f'{column}/MFT entry number',
        height=600, ))

    # for row in df.iterrows():
    #     fig.add_shape(type='line', x0=row[0]['SI creation time'], fillcolor='green')
    return fig