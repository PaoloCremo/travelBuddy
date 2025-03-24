# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container
COPY . /app

# Install necessary system dependencies
RUN apt-get update

# Install Flask and other dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 7860 for Flask
EXPOSE 7860

# Command to run the Flask app
CMD ["gunicorn", "app:app", "-b", "0.0.0.0:7860"]

