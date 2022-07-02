from dash import Dash, dcc, html, dash_table
import plotly.express as px

app = Dash(__name__)
app.title = "TODO list"

app.layout = html.Div([
   dcc.Checklist(
      options=['New York City', 'Montreal', 'San Francisco'],
      value=['Montreal']
   )
])


if __name__ == '__main__':
   app.run_server(debug=True)
