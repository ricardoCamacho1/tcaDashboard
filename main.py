import streamlit as st
import streamlit_authenticator as stauth  # pip install streamlit-authenticator
from streamlit_option_menu import option_menu
import os
import yaml
from yaml.loader import SafeLoader
import boto3
import json

import home, model


st.set_page_config(
        page_title="TCA",
        layout="wide",
)

def get_secret():
    secret_name = "your-secret-name"  # Replace with your secret name
    region_name = "your-aws-region"  # Replace with your AWS region
    # Create a Secrets Manager client
    client = boto3.client(
        service_name='secretsmanager',
        region_name=region_name
    )
    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except Exception as e:
        print(f"Error retrieving secret: {e}")
        return None
    secret = get_secret_value_response['SecretString']
    return json.loads(secret)

def login():
    secret_config = get_secret()
    if not secret_config:
        st.error("Could not retrieve the secret configuration.")
        return None, None, None, None

    config = yaml.load(secret_config["config.yaml"], Loader=SafeLoader)

    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_minutes'],
        config['preauthorized']
    )

    name, authentication_status, username = authenticator.login('main', fields={'Form name': 'TCA by InfinityLabs\nLogin:'})

    return authenticator, name, authentication_status, username

def logout(authenticator):
    with st.sidebar.container(border=True):
        st.subheader('Logout')
        st.checkbox('Verify logout', key='verify_logout')
        if st.session_state.verify_logout:
            authenticator.logout()


class MultiApp:

    def __init__(self):
        self.apps = []

    def add_app(self, title, func):

        self.apps.append({
            "title": title,
            "function": func
        })



    def run():

        authenticator, name, authentication_status, username = login()

        if authentication_status:

            # app = st.sidebar(
            with st.sidebar: 
                st.image('images/logo-TCA.png', width=270)       
                app = option_menu(
                    menu_title=f'Hola {name.split()[0]}!' ,
                    options=['Inicio','Modelo'],
                    icons=['house-fill','cloud-fill'],
                    menu_icon='person-fill',
                    default_index=1,
                    styles={
                        "container": {"padding": "5!important","background-color":'black'},
                        "icon": {"color": "white", "font-size": "23px"}, 
                        "nav-link": {"color":"white","font-size": "20px", "text-align": "left", "margin":"0px", "--hover-color": "#C0C0C0"},
                        "nav-link-selected": {"background-color": "#999999"},},
                    )
                logout(authenticator)
                
                    

            if app == "Inicio":
                home.app()
            if app == "Modelo":
                model.app()  



        elif authentication_status == False:
            st.error('Username/password is incorrect')
        elif authentication_status == None:
            st.warning('Please enter your username and password')   
    
             
    run()            
         
