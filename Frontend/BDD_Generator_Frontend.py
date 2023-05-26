from flask import Flask, render_template, request
import requests

app = Flask(__name__)

@app.route('/')
def load_home():
    return render_template("home.html")

@app.route('/generate', methods=['GET', 'POST'])
def get_generated_data():
    if request.method=="POST":
        operation = request.form.get("operation").lower()
        if operation == "new":
            page = request.form.get("page")
            space = request.form.get("space")
            path = request.form.get('path')
        elif operation == "update":
            page = request.form.get("page")
            space = request.form.get("space")
            path = request.form.get('path')
            file_text = request.form.get("file_text")

    if operation == "new":
        params = {'operation': operation, 'page': page, 'space': space, 'path': path}
    elif operation == "update":
        params = {'operation': operation, 'page': page, 'space': space, 'file_text':file_text}
    # x = str(requests.get("http://backend:8001/generate", params=params).text)
    x = str(requests.get("http://backend:8001/generate", params=params).text)
    return render_template("generated.html", code=x, page=page, space=space, path=path)

if __name__ == "__main__":
    app.run(port=int("8000"), debug=True)
