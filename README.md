# Notes

## Description
A simple web-app to create, edit, delete and share notes with your friends! Made with FastAPI 

## Setup
1. Clone the repository<br>
2. Make sure to install all the dependencies listed in requirements.txt within the project directory
   ```shell
    pip install -r requirements.txt
    ```
4. Create a .env file within the \NotesApp directory, then copy the output of the following command
     ```shell
    openssl rand -hex 32
    ```
    Within the .env file, write the following (remove the angle braces) and replace OUTPUT with the above
   ```shell
   SECRET_KEY=<OUTPUT>
   ```
6. Run the fastapi server by changing your current working directory into NotesApp
   ```shell
   cd NotesApp/
   fastapi dev main.py
   ```
7. You've successfully started the app!
   
## Docker
1. If you would like to run the app off of a container, follow all setup steps from 1-5.
2. Build your docker image
   ```shell
   docker build -t your_img .
   ```
   If you would like to have your current database on the container, edit the .dockerignore file and remove NotesApp/database.db before building the image
3. Run the docker container
   ```shell
   docker run -p 80:80 your_img
   ```
