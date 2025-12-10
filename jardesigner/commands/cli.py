#!/usr/bin/env python
"""
JARDesigner command-line interface
Similar to 'jupyter notebook' or 'jupyter lab'
"""
import sys
import os
import argparse
import webbrowser
import time
from threading import Timer

def main():
    """Main entry point for jardesigner command"""
    parser = argparse.ArgumentParser(
        description='JARDesigner - Web GUI for MOOSE neuroscience simulator'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=5000,
        help='Port to run the server on (default: 5000)'
    )
    parser.add_argument(
        '--host',
        type=str,
        default='127.0.0.1',
        help='Host to bind to (default: 127.0.0.1)'
    )
    parser.add_argument(
        '--no-browser',
        action='store_true',
        help='Don\'t open browser automatically'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Run in debug mode'
    )
    
    args = parser.parse_args()
    
    # Import the server app
    try:
        from jardesigner.server.app import socketio, app
    except ImportError as e:
        print(f"Error: Could not import jardesigner server: {e}")
        print("Please make sure jardesigner is properly installed.")
        sys.exit(1)
    
    # Print startup message
    url = f"http://{args.host}:{args.port}"
    print("=" * 60)
    print("JARDesigner Server Starting...")
    print("=" * 60)
    print(f"Server URL: {url}")
    print(f"Press Ctrl+C to stop the server")
    print("=" * 60)
    
    # Open browser after a short delay
    if not args.no_browser:
        def open_browser():
            time.sleep(1.5)
            try:
                webbrowser.open(url)
                print(f"\nOpened browser at {url}")
            except Exception as e:
                print(f"\nCould not open browser: {e}")
                print(f"Please open {url} manually")
        
        Timer(0, open_browser).start()
    
    # Start the server
    try:
        socketio.run(
            app,
            host=args.host,
            port=args.port,
            debug=args.debug,
            use_reloader=False
        )
    except KeyboardInterrupt:
        print("\n\nShutting down JARDesigner server...")
    except Exception as e:
        print(f"\nError starting server: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
