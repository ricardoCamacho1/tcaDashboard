# Streamlit Dashboard

This repository contains a Streamlit dashboard for visualizing data. 

## Installation

To run the dashboard, follow these steps:

1. Clone the repository.
2. Install the required dependencies by running `pip install -r requirements.txt`.
3. Run the dashboard using the command `streamlit run main.py`.


## AWS Coud implementation

1. Create an EC2 instance on AWS.
2. Copy the dashboard folder to the instance via scp.
3. Once the dashboard is copied, ssh into the instance.
4. Build the docker image using the command `docker build -t streamlit-dashboard .`
5. Create a ECR repository and push the image to the repository.
6. Create a ECS cluster and task definition. (Make sure to give the correct permissions to the task role including the ECR permissions an  S3 permissions)
7. Create a service and run the task on the cluster.
8. Access the dashboard using the public IP of the instance.
## Usage

Once the dashboard is running, you can access it by opening the provided URL in your web browser. The dashboard allows you to interact with the data and explore various visualizations.

In case you want to deploy the dashboard on AWS, you can follow the steps mentioned above and access the dashboard using the public IP of the instance on which the dashboard is running. (Make sure to open the required ports in the security group and in the task definition)

## License

This project is licensed under the [MIT License](LICENSE).
