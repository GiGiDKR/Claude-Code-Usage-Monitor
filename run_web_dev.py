"""
Development server launcher for the Claude Monitor Web API.

This script provides an easy way to start the development server
with proper configuration and logging.
"""

import logging
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def setup_development_environment():
    """Setup development environment."""
    # Create logs directory
    logs_dir = project_root / "logs"
    logs_dir.mkdir(exist_ok=True)

    # Setup basic logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(logs_dir / "dev_server.log"),
        ],
    )


def main():
    """Main entry point for development server."""
    setup_development_environment()

    logger = logging.getLogger("dev_server")
    logger.info("Starting Claude Monitor Web API development server...")

    try:
        import uvicorn

        from web.api.main import app

        # Configure uvicorn for development
        config = uvicorn.Config(
            app,
            host="127.0.0.1",
            port=8000,
            reload=True,
            reload_dirs=[str(project_root)],
            log_level="info",
            access_log=True,
        )

        server = uvicorn.Server(config)

        logger.info("Server will be available at:")
        logger.info("  - API: http://127.0.0.1:8000")
        logger.info("  - Docs: http://127.0.0.1:8000/api/docs")
        logger.info("  - ReDoc: http://127.0.0.1:8000/api/redoc")
        logger.info("Press Ctrl+C to stop the server")

        server.run()

    except ImportError as e:
        logger.error(f"Missing dependencies: {e}")
        logger.error("Please install the web dependencies:")
        logger.error("  pip install fastapi uvicorn[standard] pydantic websockets")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
