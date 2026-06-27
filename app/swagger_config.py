from flasgger import Swagger


swagger_template = {
    "swagger": "2.0",
    "info": {
        "title": "Customer Support Ticket Management API",
        "description": "Production-ready Flask API for support ticket workflows.",
        "version": "1.0.0",
    },
    "securityDefinitions": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "Use: Bearer <access_token>",
        }
    },
}


def init_swagger(app):
    Swagger(app, template=swagger_template)
