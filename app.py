from flask import Flask, render_template

# Initialize the Flask application
app = Flask(__name__)


# Define the route for the main page
@app.route("/")
def index():
    """
    This function handles requests to the root URL and renders the index.html page.
    """
    return render_template("index.html")


# Run the Flask application
if __name__ == "__main__":
    # Setting debug=True enables auto-reloading when changes are made
    app.run(debug=True)
