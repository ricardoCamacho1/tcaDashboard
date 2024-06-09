# Use an official Python runtime as a parent image
FROM python:3.10

# Expose port 8501 to allow external access to the Streamlit app
EXPOSE 8501

# Update the package list and install necessary packages
RUN apt-get update && apt-get install -y \
    build-essential \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install the required Python packages specified in requirements.txt
RUN pip install -r requirements.txt

# Define the entry point command to run the Streamlit app
ENTRYPOINT ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]

