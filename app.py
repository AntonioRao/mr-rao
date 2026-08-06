"""Mr. Rao — entry point for the local web server."""
from __future__ import annotations

import config
from mr_rao import create_app

app = create_app()

if __name__ == "__main__":
    print(f"{config.APP_NAME} v{config.APP_VERSION}")
    print(f"→ http://{config.HOST}:{config.PORT}")
    print(f"   debug={config.DEBUG}")
    app.run(debug=config.DEBUG, host=config.HOST, port=config.PORT, use_reloader=config.DEBUG)
