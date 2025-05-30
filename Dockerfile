# Dockerfile for Fedora-based Flask app
FROM fedora:latest

# Install system dependencies
RUN dnf -y update && \
    dnf -y install python3 python3-pip python3-devel gcc libffi-devel openssl-devel cairo-devel pkgconfig cmake && \
    dnf clean all

# Set workdir
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose the port Flask will run on
EXPOSE 5000

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# Run the application with eventlet for Flask-SocketIO
CMD ["python3", "-m", "flask", "run"]
