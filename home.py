import streamlit as st
import streamlit_shadcn_ui as ui
import pandas as pd
from local_components import card_container
import plotly.express as px
import boto3
import io


def compact_number(num):
    if num >= 1_000_000:
        compact_num = f'{num / 1_000_000:.2f}M'
    elif num >= 1_000:
        compact_num = f'{num / 1_000:.2f}K'
    else:
        compact_num = f'{num:.2f}'
    
    compact_num = compact_num.rstrip('0').rstrip('.')
    return compact_num

ONE_DAY_SECONDS = 86400

@st.cache_data(ttl=ONE_DAY_SECONDS)
def get_s3_data(bucket_name, file_name):
    s3 = boto3.resource('s3')
    obj = s3.Object(bucket_name, file_name)
    body = obj.get()['Body'].read()
    data = pd.read_parquet(io.BytesIO(body), engine='pyarrow')
    return data

def app():
    st.title('Tablero de Ingresos de Reservaciones de Hotel')

    bucket_name = 'tcadata'
    
    data = get_s3_data(bucket_name, 'reservaciones_dashboard.parquet')
    churn_data = get_s3_data(bucket_name, 'features_dashboard.parquet')
    
    selected_hotel = st.sidebar.selectbox('Selecciona Hotel', ['HOTEL 1'])
    filtered_data = data[data['empresa'] == selected_hotel].copy()
    filtered_churn = churn_data[churn_data['empresa'] == selected_hotel].copy()

    years = [2019, 2020, 'Todos']

    selected_year = st.sidebar.selectbox('Selecciona Año', years)

    if selected_year != "Todos":
        year_data = data[data['fecha_reservacion'].dt.year == selected_year]
        months = year_data['fecha_reservacion'].dt.month_name().unique()
        months = sorted(months, key=lambda x: pd.to_datetime(x, format='%B').month)
    else:
        months = data['fecha_reservacion'].dt.month_name().unique()
        months = sorted(months, key=lambda x: pd.to_datetime(x, format='%B').month)

    months.insert(0, "Todos")
    selected_month = st.sidebar.selectbox('Selecciona Mes', months, disabled=(selected_year == "Todos"))

    if selected_year != "Todos":
        if selected_month != "Todos":
            month_number = pd.to_datetime(selected_month, format='%B').month
            filtered_data = data[(data['fecha_reservacion'].dt.year == selected_year) & 
                                 (data['fecha_reservacion'].dt.month == month_number)].copy()
            filtered_churn = churn_data[(churn_data['fecha_reservacion'].dt.year == selected_year) &
                                        (churn_data['fecha_reservacion'].dt.month == month_number)].copy()
        else:
            filtered_data = data[data['fecha_reservacion'].dt.year == selected_year].copy()
            filtered_churn = churn_data[churn_data['fecha_reservacion'].dt.year == selected_year].copy()
    else:
        filtered_data = data.copy()
        filtered_churn = churn_data.copy()

    date_pick = st.sidebar.date_input('Selecciona Fecha para Churn Rate', value=pd.to_datetime('2020-04-30'))
    selected_delta = st.sidebar.selectbox('Selecciona Periodo para Churn Rate', ['1 año', '6 meses', '3 meses', '1 mes'])

    delta_mapping = {
        '1 año': 365,
        '6 meses': 180,
        '3 meses': 90,
        '1 mes': 30
    }
    number_of_days = delta_mapping[selected_delta]

    filtered_churn.loc[:, 'time_since_last_res'] = (pd.to_datetime(date_pick) - filtered_churn['fecha_reservacion']).dt.days.astype(int)
    filtered_churn.loc[:, 'churn'] = filtered_churn['time_since_last_res'] > number_of_days

    total_cancelaciones = filtered_data[filtered_data['reservacion'] == 0].shape[0]
    total_reservaciones = filtered_data[filtered_data['reservacion'] == 1].shape[0]
    tarifa_total = filtered_data['tfa_total'].sum()

    churn_rate = filtered_churn['churn'].sum() / len(filtered_churn) * 100

    cols = st.columns(4)
    with cols[0]:
        ui.card(title="Cancelaciones Totales", content=compact_number(total_cancelaciones), key="card1").render()
    with cols[1]:
        ui.card(title="Reservaciones Exitosas", content=compact_number(total_reservaciones), key="card2").render()
    with cols[2]:
        ui.card(title="Tarifa Total", content=f"${compact_number(tarifa_total)}", key="card3").render()
    with cols[3]:
        ui.card(title="Tasa de Churn", content=f"{churn_rate:.1f}%", key="card4").render()

    filtered_data = filtered_data[filtered_data['reservacion'] == 1].copy()
    filtered_data.loc[:, 'YearMonth'] = filtered_data['fecha_reservacion'].dt.to_period('M').astype(str)
    aggregated_data = filtered_data.groupby('YearMonth')['tfa_total'].sum().reset_index()

    aggregated_data.columns = ['Date', 'Total_TFA']

    with card_container(key="chart1"):
        st.subheader('Ingresos Mensuales')
        st.vega_lite_chart(aggregated_data, {
            'mark': {'type': 'bar', 'tooltip': True, 'fill': 'rgb(166,232,246)', 'cornerRadiusEnd': 4 },
            'encoding': {
                'x': {'field': 'Date', 'type': 'ordinal', 'axis': {'title': 'Date (Month and Year)'}},
                'y': {'field': 'Total_TFA', 'type': 'quantitative', 'axis': {'title': 'Tarifa Total'}},
            },
        }, use_container_width=True)

    room_type_revenue = filtered_data.groupby('tipo_habitacion')['tfa_total'].sum().reset_index()
    canal_revenue = filtered_data.groupby('canal')['tfa_total'].sum().reset_index()

    top_clients = filtered_churn.sort_values(by='total_expense', ascending=False).head(10)

    top_clients['id_cliente'] = top_clients['id_cliente'].astype(int)
    top_clients['id_cliente'] = top_clients['id_cliente'].astype(str)

    for column in top_clients.select_dtypes(include=['int64', 'float64']).columns:
        top_clients[column] = top_clients[column].apply(compact_number)  


    with card_container(key="chart10"):
        st.subheader('Top 10 Clientes con Mayor Gasto')
        ui.table(top_clients.astype(str))

    fig1 = px.treemap(room_type_revenue, 
                      path=[px.Constant("Todos"), 'tipo_habitacion'], 
                      values='tfa_total')
    fig1.update_layout(width=800, height=650)

    fig2 = px.treemap(canal_revenue,
                      path=[px.Constant("Todos"), 'canal'],
                      values='tfa_total')
    fig2.update_layout(width=800, height=650)

    with card_container(key="chart2"):
        cols = st.columns(2)
        with cols[0]:
                st.subheader('Ingresos por Tipo de Habitación ')
                st.plotly_chart(fig1, use_container_width=True)
        with cols[1]:
                st.subheader('Ingresos por Canal')
                st.plotly_chart(fig2, use_container_width=True)

    package_revenue = filtered_data.groupby('paquete')['tfa_total'].sum().reset_index()
    package_revenue = package_revenue.sort_values('tfa_total', ascending=False)
    package_revenue['tfa_total'] = package_revenue['tfa_total'].apply(compact_number)

    country_revenue = filtered_data.groupby('pais')['tfa_total'].sum().reset_index()
    country_revenue = country_revenue.sort_values('tfa_total', ascending=False)
    country_revenue['tfa_total'] = country_revenue['tfa_total'].apply(lambda x: f"${compact_number(x)}")

    with card_container(key="table2"):
        cols = st.columns(2)
        with cols[0]:
            st.subheader('Ingresos por Paquete')
            ui.table(package_revenue.head())
        with cols[1]:
            st.subheader('Ingresos por País')
            ui.table(country_revenue.head())

    agency_revenue = filtered_data.groupby('agencia')['tfa_total'].sum().reset_index()
    top_10_agency_revenue = agency_revenue.nlargest(10, 'tfa_total').sort_values('tfa_total', ascending=True)

    status_reservations = filtered_data['estatus_reservacion'].value_counts().reset_index()
    status_reservations.columns = ['estatus_reservacion', 'num_reservations']

    with card_container(key="chart5"):
        cols = st.columns(2)
        with cols[0]:
            st.subheader('Ingresos por Agencia (Top 10)')
            st.subheader('    ')
            st.vega_lite_chart(top_10_agency_revenue, {
                'width': 'container',
                'height': 550,
                'mark': {
                    'type': 'bar', 
                    'tooltip': True, 
                    'fill': 'rgb(166,232,246)', 
                    'cornerRadiusEnd': 4
                },
                'encoding': {
                    'y': {
                        'field': 'agencia', 
                        'type': 'ordinal', 
                        'axis': {
                            'title': 'Agencia',
                        },
                        'sort': '-x'
                    },
                    'x': {
                        'field': 'tfa_total', 
                        'type': 'quantitative', 
                        'axis': {'title': 'Tarifa Total'}
                    }
                },
                'config': {
                    'view': {'stroke': 'transparent'},
                    'padding': {'left': 200, 'right': 10, 'top': 10, 'bottom': 10}
                }
            }, use_container_width=True)
        with cols[1]:

            segment_revenue = filtered_data.groupby('segmento')['tfa_total'].sum().reset_index()
            fig3 = px.treemap(segment_revenue, 
                        path=[px.Constant("Todos"), 'segmento'], 
                        values='tfa_total')
            fig3.update_layout(width=800, height=650)
            st.subheader('Ingresos por Segmento ')
            st.plotly_chart(fig3, use_container_width=True)   

    with card_container(key="chart5"):
        st.subheader('Estatus de Reservaciones')
        fig = px.pie(status_reservations, values='num_reservations', names='estatus_reservacion', hole=0.5)
        fig.update_traces(text=status_reservations['estatus_reservacion'], textposition='outside', textfont=dict(size=14))
        fig.update_layout(
                legend=dict(
                    font=dict(size=14)  # Adjust the font size of the legend labels as needed
                ),
        )
        st.plotly_chart(fig, use_container_width=False)


    with card_container(key="chart6"):
        filtered_data = filtered_data[filtered_data['num_noches'] < 100].copy()
        st.subheader('Relación entre Tarifa Total y Número de Noches')
        fig_scatter = px.scatter(filtered_data, x='num_noches', y='tfa_total', color_discrete_sequence=['rgb(166,232,246)'])
        fig_scatter.update_layout(xaxis_title='Número de Noches', yaxis_title='Tarifa Total')
        st.plotly_chart(fig_scatter, use_container_width=True)

    with card_container(key="chart7"):
        filtered_data = filtered_data[filtered_data['num_noches'] < 20].copy()
        st.subheader('Distribución del Número de Noches')
        st.vega_lite_chart(filtered_data, {
            'mark': {'type':'bar', 'fill': 'rgb(166,232,246)'},
            'encoding': {
                'x': {'field': 'num_noches', 'bin':{'maxbins': 50}, 'axis': {'title': 'Número de Noches Menores a 20 días'}},
                'y': {'aggregate': 'count', 'axis': {'title': 'Conteo'}}
            }
        }, use_container_width=True)
