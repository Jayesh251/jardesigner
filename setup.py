from setuptools import setup, find_packages
from setuptools.command.install import install
from setuptools.command.develop import develop
import subprocess
import os
import sys

class BuildFrontend:
    """Mixin class to build frontend during installation"""
    
    def run_frontend_build(self):
        """Build the frontend using npm"""
        frontend_dir = os.path.join(os.path.dirname(__file__), 'frontend')
        
        if not os.path.exists(frontend_dir):
            print("Warning: frontend directory not found, skipping frontend build")
            return
            
        print("=" * 60)
        print("Building frontend assets...")
        print("=" * 60)
        try:
            # Install npm dependencies
            print("Installing npm dependencies...")
            subprocess.check_call(['npm', 'install'], cwd=frontend_dir)
            
            # Build frontend
            print("Building frontend with Vite...")
            subprocess.check_call(['npm', 'run', 'build'], cwd=frontend_dir)
            
            print("=" * 60)
            print("Frontend build completed successfully!")
            print("=" * 60)
        except subprocess.CalledProcessError as e:
            print(f"Warning: Frontend build failed: {e}")
            print("You can build it manually later with:")
            print("  cd frontend && npm install && npm run build")
        except FileNotFoundError:
            print("Warning: npm not found. Frontend will not be built.")
            print("Please install Node.js and npm, then run:")
            print("  cd frontend && npm install && npm run build")

class InstallWithFrontend(install, BuildFrontend):
    """Custom install command that builds frontend"""
    
    def run(self):
        self.run_frontend_build()
        install.run(self)

class DevelopWithFrontend(develop, BuildFrontend):
    """Custom develop command that builds frontend"""
    
    def run(self):
        self.run_frontend_build()
        develop.run(self)

# Read requirements from backend/requirements.txt
requirements_path = os.path.join(os.path.dirname(__file__), 'backend', 'requirements.txt')
with open(requirements_path) as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name='jardesigner',
    version='0.1.0',
    description='A web-based GUI for MOOSE neuroscience simulator',
    long_description=open('README.md').read() if os.path.exists('README.md') else '',
    long_description_content_type='text/markdown',
    author='MOOSE Development Team',
    author_email='',
    url='https://github.com/upibhalla/jardesigner',
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'jardesigner=jardesigner.commands.cli:main',
        ],
    },
    cmdclass={
        'install': InstallWithFrontend,
        'develop': DevelopWithFrontend,
    },
    python_requires='>=3.7',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering',
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
    ],
)
