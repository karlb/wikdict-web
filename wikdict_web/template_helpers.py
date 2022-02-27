from myapp import app


@app.context_processor
def inject_app_name():
    return dict(app_name="MyApp")
