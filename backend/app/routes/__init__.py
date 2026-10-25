def register_blueprints(app):
    from . import analysis, auth, cabinet, demo, health, history, products

    for module in (health, auth, analysis, history, products, cabinet, demo):
        app.register_blueprint(module.bp)
