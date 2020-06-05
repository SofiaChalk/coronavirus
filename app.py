import pandas as pd
from datetime import date, datetime, timedelta
import dash_table
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash.dependencies
import plotly.express as px

# Url where data will be found
Confirmed_url = r'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data' \
                r'/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv '
Deaths_url = r'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data' \
             r'/csse_covid_19_time_series/time_series_covid19_deaths_global.csv '
Recovered_url = r'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data' \
                r'/csse_covid_19_time_series/time_series_covid19_recovered_global.csv '
total_url = r'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/web-data/data/cases_country.csv'
continent_url = r'https://raw.githubusercontent.com/dbouquin/IS_608/master/NanosatDB_munging/Countries-Continents.csv'

# Initialise the dash app
app = dash.Dash(__name__)
# Initialise Heroku
server = app.server

def prepare_data(Confirmed_url, Deaths_url, Recovered_url, total_url, continent_url):
    global last_updated_df
    global confirmed_deaths_df
    global total_last_updated_df
    global shown_countries
    global total_df
    global last_updated
    global sum_data_daily_df

    # Read .csv from github
    Confirmed_df = pd.read_csv(Confirmed_url, index_col=False)
    Deaths_df = pd.read_csv(Deaths_url, index_col=False)
    Recovered_df = pd.read_csv(Recovered_url, index_col=False)
    total_df = pd.read_csv(total_url, index_col=False)
    continent_df = pd.read_csv(continent_url, index_col=False)

    # Rename columns
    Deaths_df.rename(columns={'Country/Region': 'Location'}, inplace=True)
    Confirmed_df.rename(columns={'Country/Region': 'Location'}, inplace=True)
    Recovered_df.rename(columns={'Country/Region': 'Location'}, inplace=True)
    total_df.rename(columns={'Country_Region': 'Location', 'Long_': 'Long', 'Last_Update': 'Last Update'}, inplace=True)

    # Data cleaning
    # Drop columns
    Deaths_df.drop(['Province/State', 'Lat', 'Long'], axis=1, inplace=True)
    Confirmed_df.drop(['Province/State', 'Lat', 'Long'], axis=1, inplace=True)
    Recovered_df.drop(['Province/State', 'Lat', 'Long'], axis=1, inplace=True)
    total_df.drop(['People_Tested', 'People_Hospitalized'], axis=1, inplace=True)

    # Swap rows & columns
    Confirmed_df = Confirmed_df.melt(id_vars=["Location"],
                                     var_name="Date",
                                     value_name="Total Confirmed")
    Deaths_df = Deaths_df.melt(id_vars=["Location"],
                               var_name="Date",
                               value_name="Total Deaths")
    Recovered_df = Recovered_df.melt(id_vars=["Location"],
                                     var_name="Date",
                                     value_name="Total Recovered")
    # Change data type to integer and date
    Confirmed_df['Total Confirmed'] = Confirmed_df['Total Confirmed'].astype(int)
    Deaths_df['Total Deaths'] = Deaths_df['Total Deaths'].astype(int)
    Recovered_df['Total Recovered'] = Recovered_df['Total Recovered'].astype(int)
    Confirmed_df['Date'] = Confirmed_df['Date'].apply(lambda x: datetime.strptime(x, '%m/%d/%y').date())
    Deaths_df['Date'] = Deaths_df['Date'].apply(lambda x: datetime.strptime(x, '%m/%d/%y').date())
    Recovered_df['Date'] = Recovered_df['Date'].apply(lambda x: datetime.strptime(x, '%m/%d/%y').date())
    total_df['Last Update'] = total_df['Last Update'].apply(lambda x: datetime.strptime(x, '%Y-%m-%d %H:%M:%S').date())

    # Group by as there were a few countries with more than one rows per day (eg.UK for mainland & UK for Isle of Man)
    Confirmed_df = Confirmed_df.groupby(['Location', 'Date'])['Total Confirmed'].sum().to_frame()
    Confirmed_df = Confirmed_df.assign(**Confirmed_df.index.to_frame()).reset_index(drop=True)
    Deaths_df = Deaths_df.groupby(['Location', 'Date'])['Total Deaths'].sum().to_frame()
    Deaths_df = Deaths_df.assign(**Deaths_df.index.to_frame()).reset_index(drop=True)
    Recovered_df = Recovered_df.groupby(['Location', 'Date'])['Total Recovered'].sum().to_frame()
    Recovered_df = Recovered_df.assign(**Recovered_df.index.to_frame()).reset_index(drop=True)

    # Change column order
    Confirmed_df = Confirmed_df[['Location', 'Date', 'Total Confirmed']]
    Deaths_df = Deaths_df[['Location', 'Date', 'Total Deaths']]
    Recovered_df = Recovered_df[['Location', 'Date', 'Total Recovered']]

    # Find all unique countries in the dataframe and add to list
    shown_countries = []
    shown_countries = Confirmed_df['Location'].unique().tolist()

    # Create an empty df
    new_Confirmed_df = pd.DataFrame(columns=['Location', 'Date', 'Total Confirmed', 'New Confirmed'])
    new_Deaths_df = pd.DataFrame(columns=['Location', 'Date', 'Total Deaths', 'New Deaths'])
    new_Recovered_df = pd.DataFrame(columns=['Location', 'Date', 'Total Recovered', 'New Recovered'])

    # Create a country_df with data for each country, diff to fine New cases per day, append to new_Confirmed_df
    for country in shown_countries:
        confirmed_country_df = Confirmed_df.loc[Confirmed_df['Location'] == country]
        confirmed_country_df = confirmed_country_df.sort_values('Date')
        confirmed_country_df['New Confirmed'] = confirmed_country_df['Total Confirmed'].diff().fillna(0).astype(int)
        new_Confirmed_df = new_Confirmed_df.append(confirmed_country_df)

        Deaths_country_df = Deaths_df.loc[Deaths_df['Location'] == country]
        Deaths_country_df = Deaths_country_df.sort_values('Date')
        Deaths_country_df['New Deaths'] = Deaths_country_df['Total Deaths'].diff().fillna(0).astype(int)
        new_Deaths_df = new_Deaths_df.append(Deaths_country_df)

        Recovered_country_df = Recovered_df.loc[Recovered_df['Location'] == country]
        Recovered_country_df = Recovered_country_df.sort_values('Date')
        Recovered_country_df['New Recovered'] = Recovered_country_df['Total Recovered'].diff().fillna(0).astype(int)
        new_Recovered_df = new_Recovered_df.append(Recovered_country_df)

    for i in range(len(new_Confirmed_df) - 1):
        if new_Confirmed_df.iloc[i + 1, 3] < 0:
            new_Confirmed_df.iloc[i + 1, 3] = 0

    for i in range(len(new_Deaths_df) - 1):
        if new_Deaths_df.iloc[i + 1, 3] < 0:
            new_Deaths_df.iloc[i + 1, 3] = 0

    for i in range(len(new_Recovered_df) - 1):
        if new_Recovered_df.iloc[i + 1, 3] < 0:
            new_Recovered_df.iloc[i + 1, 3] = 0

    # Merge confirmed and deaths dfs
    confirmed_deaths_df = new_Confirmed_df.merge(new_Deaths_df, left_on=['Location', 'Date'],
                                                 right_on=['Location', 'Date'])
    # Merge df with continent df
    confirmed_deaths_df = confirmed_deaths_df.merge(continent_df, left_on='Location', right_on='Country')
    confirmed_deaths_df = confirmed_deaths_df.drop('Country', axis=1)

    # Create a df with only lat, long of each location
    lat_df = total_df[['Location', 'Lat', 'Long']].copy()
    # Create a df with only lat, long of each location
    iso_df = total_df[['Location', 'ISO3']].copy()

    # Merge confirmed_deaths_df with the lat, long of total_df
    confirmed_deaths_df = confirmed_deaths_df.merge(lat_df, left_on='Location', right_on='Location', how='left')
    # Merge confirmed_deaths_df with the lat, long of total_df
    confirmed_deaths_df = confirmed_deaths_df.merge(iso_df, left_on='Location', right_on='Location', how='left')

    # Merge total_df with continent_df
    total_df = total_df.merge(continent_df, left_on='Location', right_on='Country', how='left')
    total_df = total_df.drop('Country', axis=1)

    total_df['Continent'] = total_df['Continent'].fillna('Other')

    # Create a df with the total of most recent data
    total_last_updated_df = total_df.drop(['Lat', 'Long', 'Incident_Rate', 'Mortality_Rate', 'UID', 'ISO3'], axis=1)
    for column in ['Confirmed', 'Deaths', 'Recovered', 'Active']:
        total_last_updated_df[column] = total_last_updated_df[column].astype(int)

    # Find last date when data was updated
    last_updated = total_last_updated_df['Last Update'][0]
    if last_updated not in confirmed_deaths_df:
        last_updated = total_last_updated_df['Last Update'][0] - timedelta(days=1)

    # Create a df with the new cases of most recent data
    last_updated_df = confirmed_deaths_df[confirmed_deaths_df['Date'] == last_updated]

    # Create a df that summarises all Cases/Deaths for every day
    sum_data_daily_df = confirmed_deaths_df.groupby(['Date']).agg({'New Confirmed': 'sum', 'New Deaths': 'sum'})
    sum_data_daily_df = sum_data_daily_df.assign(**sum_data_daily_df.index.to_frame()).reset_index(drop=True)


def visualise_dash():

    def generate_table():
        """
        This function creates an HTML.TABLE to illustrate the 10 countries
        with the most cases for today
        :return html.table:
        """
        formatted_tday_df = last_updated_df.copy().drop(
            ['Total Confirmed', 'Total Deaths', 'Continent', 'Date', 'Lat', 'Long', 'ISO3'],
            axis=1).sort_values('New Confirmed', ascending=False)
        formatted_tday_df['New Confirmed'] = formatted_tday_df['New Confirmed'].apply('{:,}'.format)
        formatted_tday_df['New Deaths'] = formatted_tday_df['New Deaths'].apply('{:,}'.format)

        return dash_table.DataTable(
            data=formatted_tday_df.to_dict('records'),
            columns=[{'id': c, 'name': c} for c in formatted_tday_df.columns],
            style_cell={'padding': '1px', 'textAlign': 'left', 'border': '1px solid rgb(237, 237, 237)',
                        'width': 'auto', 'font_family': 'sans-serif',
                        'font_size': '16px', 'color': 'rgb(93, 103, 110)'},
            style_table={'height': '500px', 'width': '600px', 'overflowY': 'auto'},
            style_header={'border': '1px solid rgb(237, 237, 237)', 'backgroundColor': 'white',
                          'fontWeight': 'bold', 'textAlign': 'center', 'color': 'rgb(50, 119, 168)'},
            style_data={'textAlign': 'center', 'width': 'auto'}
        )

    def cases_line_graph():
        bar_df = sum_data_daily_df.copy()
        # bar_df.loc[:, 'Cases'] = bar_df.loc[:, 'Cases'].apply('{:,}'.format)
        # bar_df.loc[:, 'Deaths'] = bar_df.loc[:, 'Deaths'].apply('{:,}'.format)
        fig = px.line(data_frame=bar_df,
                      x='Date',
                      y='New Confirmed',
                      template='none')
        fig.update_layout(title_text='Confirmed Cases over time worldwide',
                          width=740, height=500)
        return fig

    def deaths_line_graph():
        bar_df = sum_data_daily_df.copy()
        fig = px.line(data_frame=bar_df,
                      x='Date',
                      y='New Deaths',
                      template='none')
        fig.update_layout(title_text='Confirmed Deaths over time worldwide',
                          width=740, height=500)

        return fig

    # Prepare the page layout
    app.layout = html.Div(className='overall-background',
                          children=[
                              html.H1(children=['COVID-19 Dashboard']),
                              html.P(children='*Latest Updated on: ' + str(last_updated),
                                     style={"font_size": "xx-small",
                                            'textAlign': 'center'}),

                              html.Div(className='row', style={'display': 'inline-block'}, children=[
                                  html.Div(className='firsttable', children=[
                                      html.Div(className='newcases_table', children=[
                                          html.P(html.Strong(f"{last_updated_df['New Confirmed'].sum():,d}")),
                                          dcc.Markdown('''*New Cases*''')]),
                                      html.Div(className='totalcases_table', children=[
                                          html.P(html.Strong(f"{total_last_updated_df['Confirmed'].sum():,d}")),
                                          dcc.Markdown('''*Total Cases*''')]),
                                      html.Div(className='newdeaths_table', children=[
                                          html.P(html.Strong(f"{last_updated_df['New Deaths'].sum():,d}")),
                                          dcc.Markdown('''*New Deaths*''')]),
                                      html.Div(className='totaldeaths_table', children=[
                                          html.P(html.Strong(f"{total_last_updated_df['Deaths'].sum():,d}")),
                                          dcc.Markdown('''*Total Deaths*''')]),
                                      html.Div(className='totalactive_table', children=[
                                          html.P(html.Strong(f"{total_last_updated_df['Active'].sum():,d}")),
                                          dcc.Markdown('''*Total Active*''')])
                                  ]),
                                  html.Div(className='map', children=[
                                      html.Div(children=[
                                          dcc.Dropdown(
                                              id='casesordeaths',
                                              options=[{'label': 'Confirmed', 'value': 'Confirmed'},
                                                       {'label': 'Deaths', 'value': 'Deaths'}],
                                              multi=False,
                                              value='Confirmed',
                                              style={'width': '150px',
                                                     'textAlign': 'center',
                                                     'color': 'black',
                                                     'backgroundColor': 'white'}),
                                          dcc.Graph(id='Interactive Map')])])]),
                              html.Div(className='row', style={'display': 'inline-block'}, children=[
                                  html.Div(className='lineC', children=[
                                      dcc.Graph(figure=cases_line_graph())]),
                                  html.Div(className='lineD', children=[
                                      dcc.Graph(figure=deaths_line_graph())])]),

                              html.Div(className='row', style={'display': 'inline-block'}, children=[
                                  html.Div(className='dd1', children=[
                                      dcc.Dropdown(
                                          id='country',
                                          options=[{'label': i, 'value': i} for i in sorted(shown_countries)],
                                          multi=False,
                                          value='United Kingdom',
                                          style={'width': '200px',
                                                 'textAlign': 'center',
                                                 'color': 'black',
                                                 'backgroundColor': 'white'})]),
                                  html.Div(className='dd2', children=[
                                      dcc.Dropdown(
                                          id='casesordeaths3',
                                          options=[{'label': 'Confirmed', 'value': 'Confirmed'},
                                                   {'label': 'Deaths', 'value': 'Deaths'}],
                                          multi=False,
                                          value='Confirmed',
                                          style={'width': '150px',
                                                 'textAlign': 'center',
                                                 'color': 'black',
                                                 'backgroundColor': 'white'})])]),

                              html.Div(className='row', children=[
                                  html.Div(className='bar', children=[
                                      dcc.Graph(id='Bar1')]),
                                  html.Div(className='casespercountry', children=[
                                      html.P(id="status")])]),

                              html.Div(className='row', style={'display': 'inline-block'}, children=[
                                  html.Div(className='fulltable', children=[
                                      html.P(children='Highest Cases Worldwide for ' + str(last_updated),
                                             style={"font_size": "23px",
                                                    "font_color": "grey",
                                                    'textAlign': 'center'}),
                                      generate_table()]),
                                  html.Div(className='pie', children=[
                                      dcc.Dropdown(
                                          id='casesordeaths2',
                                          options=[{'label': 'Confirmed', 'value': 'Confirmed'},
                                                   {'label': 'Deaths', 'value': 'Deaths'}],
                                          multi=False,
                                          value='Confirmed',
                                          style={'width': '150px',
                                                 'textAlign': 'center',
                                                 'color': 'black',
                                                 'backgroundColor': 'white'}),
                                      dcc.Graph(id='Pie')])])])

    @app.callback(dash.dependencies.Output('Interactive Map', 'figure'),
                  [dash.dependencies.Input('casesordeaths', 'value')])
    def update_map_graph(c_or_d):
        map_df = confirmed_deaths_df.sort_values('Date', ascending=True).copy()
        # map_df.loc[:, 'Cases'] = map_df.loc[:, 'Cases'].apply('{:,}'.format)
        # map_df.loc[:, 'Deaths'] = map_df.loc[:, 'Deaths'].apply('{:,}'.format)
        # map_df['Population'].astype(str)
        map_df['Total ' + c_or_d] = map_df['Total ' + c_or_d].astype(int)

        fig = px.choropleth(data_frame=map_df,
                            locations="ISO3",
                            color='Total ' + c_or_d,
                            hover_name='Location',
                            hover_data=["Location", 'Date', 'Total ' + c_or_d],
                            animation_frame=map_df["Date"].astype(str),
                            range_color=[10, max(map_df['Total ' + c_or_d])],
                            color_continuous_scale=[(0.0, "#ffe6e6"), (0.001, "#ffe6e6"),
                                                    (0.002, "#ffcccc"), (0.003, "#ffcccc"),
                                                    (0.004, "#ffb3b3"), (0.005, "#ffb3b3"),
                                                    (0.006, " #ff9999"), (0.007, " #ff9999"),
                                                    (0.008, "#ffb399"), (0.009, "#ffb399"),
                                                    (0.01, "#ffcc99"), (0.02, "#ffcc99"),
                                                    (0.03, "#ffe699"), (0.04, "#ffe699"),
                                                    (0.05, "#ffff99"), (0.06, "#ffff99"),
                                                    (0.07, "#e6ff99"), (0.08, "#e6ff99"),
                                                    (0.09, "#ccff99"), (0.1, "#ccff99"),
                                                    (0.11, "#b3ff99"), (0.12, "#b3ff99"),
                                                    (0.13, "#99ff99"), (0.14, "#99ff99"),
                                                    (0.15, "#99ffb3"), (0.16, "#99ffb3"),
                                                    (0.17, "#99ffcc"), (0.18, "#99ffcc"),
                                                    (0.19, "#99ffe6"), (0.2, "#99ffe6"),
                                                    (0.21, "#99ffff"), (0.22, "#99ffff"),
                                                    (0.23, "#99e6ff"), (0.24, "#99e6ff"),
                                                    (0.25, "#99ccff"), (0.26, "#99ccff"),
                                                    (0.27, "#99b3ff"), (0.28, "#99b3ff"),
                                                    (0.29, "#9999ff"), (0.30, "#9999ff"),
                                                    (0.31, "#b399ff"), (0.32, "#b399ff"),
                                                    (0.33, "#cc99ff"), (0.34, "#cc99ff"),
                                                    (0.35, "#e699ff"), (0.36, "#e699ff"),
                                                    (0.37, "#ff99ff"), (0.38, "#ff99ff"),
                                                    (0.39, "#ff99e6"), (0.40, "#ff99e6"),
                                                    (0.41, "#ff99cc"), (0.42, "#ff99cc"),
                                                    (0.43, "#ff99b3"), (0.44, "#ff99b3"),
                                                    (0.45, "#ff809f"), (0.46, "#ff809f"),
                                                    (0.47, "#ff668c"), (0.48, "#ff668c"),
                                                    (0.49, "#ff4d79"), (0.50, "#ff4d79"),
                                                    (0.51, "#ff3366"), (0.52, "#ff3366"),
                                                    (0.53, "#ff1a53"), (0.54, "#ff1a53"),
                                                    (0.55, "#ff0040"), (0.56, "#ff0040"),
                                                    (0.57, "#e60039"), (0.58, "#e60039"),
                                                    (0.59, "#cc0033"), (0.60, "#cc0033"),
                                                    (0.61, "#b3002d"), (0.62, "#b3002d"),
                                                    (0.63, "#990026"), (0.64, "#990026"),
                                                    (0.65, "#800020"), (0.66, "#800020"),
                                                    (0.67, "#66001a"), (0.68, "#66001a"),
                                                    (0.69, "#570f0f"), (0.70, "#570f0f"),
                                                    (0.71, "#521414"), (0.72, "#521414"),
                                                    (0.73, "#4d1919"), (0.74, "#4d1919"),
                                                    (0.75, "#471f1f"), (0.76, "#471f1f"),
                                                    (0.77, "#422424"), (0.78, "#422424"),
                                                    (0.79, "#3d2929"), (0.80, "#3d2929"),
                                                    (0.81, "#382e2e"), (0.82, "#382e2e"),
                                                    (0.83, "#382e2e"), (0.84, "#382e2e"),
                                                    (0.85, "#363030"), (0.86, "#363030"),
                                                    (0.87, "#333333"), (1, "#333333")])
        fig.update_layout(
            title_text='Global Spread of Coronavirus',
            width=1200,
            height=600,
            title_x=0.5,
            margin=dict(l=30, r=30, t=30, b=30),
            geo=dict(
                showframe=False,
                showcoastlines=False
            ))

        return fig

    @app.callback(dash.dependencies.Output('Pie', 'figure'),
                  [dash.dependencies.Input('casesordeaths2', 'value')])
    def update_pie_graph(c_or_d2):
        bar_df = total_df.copy()
        # Format the Percentage columns to show two decimal digits
        # pie1_df['Percentage_Cases_per_Country'] = pie1_df['Percentage_Cases_per_Country'].apply('{:.4f}%'.format)
        # pie1_df['Percentage_Deaths_per_Country'] = pie1_df['Percentage_Deaths_per_Country'].apply('{:.4f}%'.format)

        fig_pie = px.sunburst(data_frame=bar_df,
                              path=['Continent', 'Location'],
                              values=c_or_d2,
                              hover_data=['Location', 'Last Update', c_or_d2],
                              color_discrete_sequence=px.colors.qualitative.Safe
                              )

        fig_pie.update_layout(title_text='Total ' + c_or_d2 + ' by Continent',
                              title_x=0.5,
                              width=700, height=600,
                              geo=dict(
                                  showframe=False,
                                  showcoastlines=False))
        return fig_pie

    @app.callback([dash.dependencies.Output('Bar1', 'figure'),
                   dash.dependencies.Output('status', "children")],
                  [dash.dependencies.Input('country', 'value'),
                   dash.dependencies.Input('casesordeaths3', 'value')])
    def update_bar1_graph(chosen_country, c_or_d3):
        bar1_df = confirmed_deaths_df[confirmed_deaths_df['Location'] == chosen_country].copy()
        pie1_df = total_df[total_df['Location'] == chosen_country].copy()

        # bar1_df.loc[:, 'Cases'] = bar1_df.loc[:, 'Cases'].apply('{:,}'.format)
        # bar1_df.loc[:, 'Deaths'] = bar1_df.loc[:, 'Deaths'].apply('{:,}'.format)
        pie1_df.loc[:, 'Confirmed'] = pie1_df.loc[:, 'Confirmed'].copy().apply('{:,}'.format)
        pie1_df.loc[:, 'Deaths'] = pie1_df.loc[:, 'Deaths'].copy().apply('{:,}'.format)
        pie1_df.loc[:, 'Mortality_Rate'] = pie1_df.loc[:, 'Mortality_Rate'].copy().apply('{:.2f}%'.format)

        fig = px.bar(data_frame=bar1_df,
                     x='Date',
                     y='New ' + c_or_d3,
                     text='New ' + c_or_d3,
                     orientation='v',
                     hover_data=['Location', 'Date', 'New ' + c_or_d3],
                     template='none'
                     )
        fig.update_layout(title_text=c_or_d3 + ' over time per country',
                          width=1300, height=500)

        status = html.Div(className='secondtable', children=[
            html.Div(className='totalC', children=[
                html.P(html.Strong(pie1_df['Confirmed'])),
                dcc.Markdown('''*Total Cases*''')]),
            html.Div(className='totalD', children=[
                html.P(html.Strong(pie1_df['Deaths'])),
                dcc.Markdown('''*Total Deaths*''')]),
            html.Div(className='percentD', children=[
                html.P(html.Strong(pie1_df['Mortality_Rate'])),
                dcc.Markdown('''*% of Deaths*''')])])

        return fig, status

    if __name__ == '__main__':
        app.run_server()


prepare_data(Confirmed_url=Confirmed_url, Deaths_url=Deaths_url, Recovered_url=Recovered_url, total_url=total_url,
             continent_url=continent_url)
visualise_dash()
