import streamlit as st
import streamlit_shadcn_ui as ui
import pandas as pd
from local_components import card_container
import plotly.graph_objects as go
import boto3
import io
import pickle

from sklearn.metrics import f1_score, accuracy_score,recall_score, roc_curve, auc, precision_recall_curve


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

@st.cache_data(ttl=ONE_DAY_SECONDS)
def read_pickle_from_s3(bucket_name: str, key: str):
    # Create an S3 client
    s3 = boto3.client('s3')
    # Download the pickle file from S3
    s3.download_file(bucket_name, key, '/tmp/temp_model.pkl')
    # Load the pickle file
    with open('/tmp/temp_model.pkl', 'rb') as file:
        model_data = pickle.load(file)
    return model_data



def app():
    st.title('Resultados del Modelo (GradientBoostingClassifier)')
    bucket_name = 'tcadata'
    
    #predicted_data = get_s3_data(bucket_name, 'y_predict.parquet')
    churn_data = get_s3_data(bucket_name, 'features_model.parquet')
    #model = get_s3_data(bucket_name, 'modelo_limpio.py')
    #predicted_data = pd.read_csv('y_pred.csv')

    key = 'model_data.pkl'
    model_data = read_pickle_from_s3(bucket_name, key)

    # Access the loaded model and data
    model = model_data['model']
    X_test = model_data['X_test']
    y_test = model_data['y_test']
    predicted_data = model_data['y_pred']


    # Evaluación del modelo
    accuracy = accuracy_score(y_test, predicted_data) * 100
    f1 = f1_score(y_test, predicted_data, average='weighted') * 100
    recall = recall_score(y_test, predicted_data, average='weighted') *100

    # MODEL PERFORMANCE
    cols = st.columns(3)
    with cols[0]:
        ui.card(title="Exactitud", content=f"{accuracy:.2f}%", key="card1").render()
    with cols[1]:
        ui.card(title="F1-Score", content=f"{f1:.2f}%", key="card2").render()
    with cols[2]:
        ui.card(title="Recall", content=f"{recall:.2f}%", key="card3").render()

    def plot_roc_curve(model, X_test, y_test):
        y_pred_proba = model.predict_proba(X_test)[:, 1]
        fpr, tpr, _ = roc_curve(y_test, y_pred_proba)
        roc_auc = auc(fpr, tpr)

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=fpr, y=tpr, mode='lines', name='ROC curve (area = %0.2f)' % roc_auc))
        fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode='lines', name='Chance', line=dict(dash='dash')))
        
        fig.update_layout(
            title='Curva ROC',
            xaxis_title='Falsos Positivos',
            yaxis_title='Verdaderos Positivos',
            showlegend=True
        )
        return fig

    def plot_precision_recall_curve(model, X_test, y_test):
        y_pred_proba = model.predict_proba(X_test)[:, 1]
        precision, recall, _ = precision_recall_curve(y_test, y_pred_proba)

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=recall, y=precision, mode='lines', name='Precision-Recall curve'))
        
        fig.update_layout(
            title='Precision-Recall Curve',
            xaxis_title='Recall',
            yaxis_title='Precision',
            showlegend=True
        )
        return fig

    fig_roc_curve = plot_roc_curve(model, X_test, y_test)
    fig_pr_curve = plot_precision_recall_curve(model, X_test, y_test)
    with card_container(key="chart0"):
        cols = st.columns(2)
        with cols[0]:
            st.plotly_chart(fig_roc_curve, use_container_width=True)
        with cols[1]:
            st.plotly_chart(fig_pr_curve, use_container_width=True)

# FEATURE IMPORTANCE
    importances = model.feature_importances_
    features = churn_data.drop(['churn', 'client_key', 'last_visit', 'last_reservation', 
                                'time_since_last_res', 'total_people_stayed'], axis=1).columns
    feature_importances = pd.DataFrame({'Feature': features, 'Importance': importances})
    feature_importances = feature_importances.sort_values(by='Importance', ascending=False)

    with card_container(key="chart1"):
        st.subheader('Importancia de las variables en el modelo')
        fig_featureimportance = go.Figure(go.Bar(
            x=feature_importances['Importance'],
            y=feature_importances['Feature'],
            orientation='h',
            marker=dict(color=feature_importances['Importance'], colorscale='blues')
        ))
        fig_featureimportance.update_layout(
            xaxis_title='Importancia',
            yaxis_title='Variable',
            yaxis=dict(autorange="reversed")  # To display the most important features at the top
        )
        #st.plotly_chart(fig_featureimportance, use_container_width=True)
        st.vega_lite_chart(feature_importances, {
                'width': 'container',
                'height': 443,
                'mark': {
                    'type': 'bar', 
                    'tooltip': True, 
                    'fill': 'rgb(166,232,246)', 
                    'cornerRadiusEnd': 4
                },
                'encoding': {
                    'y': {
                        'field': 'Feature', 
                        'type': 'ordinal', 
                        'axis': {
                            'title': 'Variable',
                        },
                        'sort': '-x'
                    },
                    'x': {
                        'field': 'Importance', 
                        'type': 'quantitative', 
                        'axis': {'title': 'Importancia'}
                    }
                },
                'config': {
                    'view': {'stroke': 'transparent'},
                    'padding': {'left': 200, 'right': 10, 'top': 10, 'bottom': 10}
                }
            }, use_container_width=True)
    
    churn = churn_data[churn_data['churn'] == True].drop(['churn'], axis = 1)
    repitent = churn_data[churn_data['churn'] == False].drop(['churn'], axis = 1)

    def plot_distributions(df1, df2, col, titulo):
        fig = go.Figure()
        fig.add_trace(go.Histogram(x=df1[col], name='Churn', nbinsx=30, opacity=0.75, marker_color='#CB2026'))
        fig.add_trace(go.Histogram(x=df2[col], name='Repitent', nbinsx=30, opacity=0.75, marker_color='#a6e7f6'))
            
        fig.update_layout(
                title=titulo,
                barmode='overlay',
                xaxis_title=col,
                yaxis_title='Frequency',
                bargap=0.2,
                bargroupgap=0.1
        )
        fig.update_traces(opacity=0.75)
        return fig

    def plot_density(df1, df2, col, titulo):
        fig = go.Figure()
        fig.add_trace(go.Histogram(x=df1[col], name='Churn', nbinsx=30, opacity=0.5, marker_color='#CB2026', histnorm='probability density'))
        fig.add_trace(go.Histogram(x=df2[col], name='Repitent', nbinsx=30, opacity=0.5, marker_color='#a6e7f6', histnorm='probability density'))
            
        fig.update_layout(
            title=titulo,
            barmode='overlay',
            xaxis_title=col,
            yaxis_title='Density',
            bargap=0.2,
            bargroupgap=0.1,
            width=500,  # Adjust the width
            height=400  # Adjust the height
        )
        fig.update_traces(opacity=0.75)
        return fig


    def plot_box(df1, df2, col, titulo):
        fig = go.Figure()
        fig.add_trace(go.Box(y=df1[col], name='Churn', marker_color='#CB2026'))
        fig.add_trace(go.Box(y=df2[col], name='Repitent', marker_color='#a6e7f6'))
            
        fig.update_layout(
            title=titulo,
            xaxis_title='Category',
            yaxis_title=col,
            width=500, 
            height=400 
        )
        return fig

    # Example usage with columns
    fig_dist_roomtype = plot_box(churn, repitent, 'avg_days_between_visits', 'Por días estre reservaciones')
    fig_dist_estancia = plot_box(churn, repitent, 'dias_estancia', 'Por tiempo de estancia')
    fig_dist_expense = plot_box(churn, repitent, 'total_rooms_reserved', 'Por cuartos reservados')

    with card_container(key="chart2"):
        st.subheader('Distribuciones de variables')
        cols = st.columns(3)
        with cols[0]:
            st.plotly_chart(fig_dist_expense, use_container_width=True)
        with cols[1]:
            st.plotly_chart(fig_dist_roomtype, use_container_width=True)
        with cols[2]:
            st.plotly_chart(fig_dist_estancia, use_container_width=True)