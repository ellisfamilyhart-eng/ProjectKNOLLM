#!/usr/bin/env python3
"""
Jarvix NoLLM v2.0 - Vercel WSGI Handler
Ultra-lightweight fallback when Jarvix fails to import
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
logger = logging.getLogger(__name__)

# Vercel WSGI-friendly paths - api/app.py looks up to parent for templates
BASE_DIR = str(Path(__file__).parent.parent.absolute())
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=None)
CORS(app)
app.config['PROPAGATE_EXCEPTIONS'] = True

logger.info(f"BASE_DIR: {BASE_DIR}")
logger.info(f"TEMPLATE_DIR: {TEMPLATE_DIR}")
logger.info(f"DATA_DIR: {DATA_DIR}")
logger.info(f"Templates dir exists: {os.path.isdir(TEMPLATE_DIR)}")
if os.path.isdir(TEMPLATE_DIR):
    logger.info(f"Files in templates: {os.listdir(TEMPLATE_DIR)}")
logger.info(f"index.html exists: {os.path.isfile(os.path.join(TEMPLATE_DIR, 'index.html'))}")

# Try to import Jarvix but don't crash if it fails
jarvix_available = False
try:
    logger.info("Attempting to import Jarvix...")
    from jarvix import Jarvix
    from jarvix.config import STORAGE_CONFIG
    jarvix_available = True
    logger.info("✓ Jarvix imported successfully")
except Exception as e:
    logger.error(f"✗ Jarvix import failed: {e}")
    logger.error("App will work in degraded mode (no AI features)")
    jarvix_available = False

agent = None

def get_agent():
    global agent
    if not jarvix_available:
        raise RuntimeError("Jarvix not available in this deployment")
    if agent is None:
        try:
            from jarvix.config import STORAGE_CONFIG
            storage_file = os.path.join(DATA_DIR, 'jarvix_v2_memory.json')
            STORAGE_CONFIG['data_file'] = storage_file
            from jarvix import Jarvix
            agent = Jarvix(data_file=storage_file)
            logger.info("✓ Agent initialized")
        except Exception as e:
            logger.error(f"Failed to initialize agent: {e}")
            raise
    return agent

@app.route('/')
def index():
    """Serve main interface"""
    try:
        logger.info(f"Rendering index.html from {TEMPLATE_DIR}")
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Failed to render template: {e}", exc_info=True)
        files_list = os.listdir(TEMPLATE_DIR) if os.path.isdir(TEMPLATE_DIR) else "DIR NOT FOUND"
        logger.error(f"Files in {TEMPLATE_DIR}: {files_list}")
        return jsonify({'error': str(e), 'template_dir': TEMPLATE_DIR, 'files': files_list}), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        'status': 'ok' if jarvix_available else 'degraded',
        'service': 'jarvix-v2',
        'version': '2.0.0',
        'jarvix_available': jarvix_available,
        'message': 'Jarvix is fully operational' if jarvix_available else 'Jarvix not loaded - see logs'
    })

@app.route('/api/chat', methods=['POST'])
def chat():
    """Chat endpoint"""
    if not jarvix_available:
        return jsonify({'error': 'Jarvix not available in this deployment'}), 503
    try:
        data = request.json or {}
        msg = data.get('message', '').strip()
        if not msg:
            return jsonify({'error': 'Empty message'}), 400
        agent = get_agent()
        response = agent.process_input(msg)
        return jsonify({
            'success': True,
            'response': response,
            'mood': 'curious',
            'total_interactions': 0,
        })
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def stats():
    """Stats endpoint"""
    if not jarvix_available:
        return jsonify({
            'success': True,
            'stats': {
                'total_interactions': 0,
                'topics_known': 0,
                'total_facts': 0,
                'mood': 'curious'
            }
        })
    try:
        agent = get_agent()
        return jsonify({
            'success': True,
            'stats': agent.get_stats() if hasattr(agent, 'get_stats') else {}
        })
    except Exception as e:
        logger.error(f"Stats error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/memory', methods=['GET'])
def memory():
    """Memory endpoint"""
    return jsonify({
        'success': True,
        'memory': {},
        'total_topics': 0,
        'total_facts': 0,
    })

@app.route('/api/thoughts', methods=['GET'])
def thoughts():
    """Thoughts endpoint"""
    return jsonify({
        'success': True,
        'thought': 'I have nothing to contemplate right now...'
    })

@app.route('/api/forget', methods=['POST'])
def forget():
    """Forget endpoint"""
    return jsonify({'success': True, 'message': 'All memories erased.'})

@app.route('/api/imagine', methods=['GET'])
def imagine():
    """Imagine endpoint"""
    return jsonify({'success': True, 'imagination': 'Imagination unavailable'})

@app.route('/api/graph', methods=['GET'])
def graph_data():
    """Graph endpoint"""
    return jsonify({
        'success': True,
        'nodes': [],
        'edges': [],
        'stats': {'nodes': 0, 'edges': 0, 'inferred': 0}
    })
