#!/usr/bin/env python3
"""
Jarvix NoLLM v2.0 Flask Web Server - Lightweight Vercel Edition
REST API with fallback for import failures
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
import sys
import logging
import traceback

# Setup logging for Vercel
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Get directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# Initialize Flask app
app = Flask(__name__, template_folder=TEMPLATE_DIR)
CORS(app)
app.config['PROPAGATE_EXCEPTIONS'] = True

# Global agent and error tracker
agent = None
init_error = None

def get_agent():
    """Lazily initialize the Jarvix agent with detailed error logging"""
    global agent, init_error
    
    if init_error:
        raise RuntimeError(f"Agent initialization failed: {init_error}")
    
    if agent is not None:
        return agent
    
    try:
        logger.info("=" * 60)
        logger.info("Initializing Jarvix agent...")
        logger.info("=" * 60)
        
        # Try importing jarvix modules
        logger.info("Importing jarvix modules...")
        try:
            from jarvix.config import STORAGE_CONFIG
            logger.info("✓ Imported jarvix.config")
        except ImportError as e:
            logger.error(f"✗ Failed to import jarvix.config: {e}", exc_info=True)
            raise
        
        try:
            from jarvix import Jarvix
            logger.info("✓ Imported Jarvix class")
        except ImportError as e:
            logger.error(f"✗ Failed to import Jarvix: {e}", exc_info=True)
            logger.error("Full traceback:")
            traceback.print_exc()
            raise
        
        # Set storage config
        storage_file = os.path.join(DATA_DIR, 'jarvix_v2_memory.json')
        STORAGE_CONFIG['data_file'] = storage_file
        logger.info(f"Storage file: {storage_file}")
        
        # Initialize Jarvix
        logger.info("Creating Jarvix instance...")
        agent = Jarvix(data_file=storage_file)
        logger.info("✓ Jarvix agent initialized successfully")
        logger.info("=" * 60)
        
        return agent
        
    except Exception as e:
        logger.error(f"✗ Failed to initialize Jarvix agent: {e}")
        logger.error("Full traceback:")
        traceback.print_exc()
        init_error = str(e)
        raise

# ============================================================================
# ROUTES
# ============================================================================

@app.route('/')
def index():
    """Serve the main HTML interface"""
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error rendering index.html: {e}", exc_info=True)
        return jsonify({'error': 'Failed to load interface', 'details': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    try:
        agent_obj = get_agent()
        return jsonify({
            'status': 'healthy',
            'service': 'jarvix-v2',
            'version': '2.0.0',
            'agent_status': 'initialized',
            'data_dir': DATA_DIR
        })
    except Exception as e:
        logger.warning(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'service': 'jarvix-v2',
            'version': '2.0.0',
            'error': str(e),
            'data_dir': DATA_DIR
        }), 503

# ========== CORE CHAT & LEARNING ==========

@app.route('/api/chat', methods=['POST'])
def chat():
    """Process user message"""
    try:
        data = request.json or {}
        user_input = data.get('message', '').strip()
        
        if not user_input:
            return jsonify({'error': 'Empty message'}), 400
        
        agent_obj = get_agent()
        response = agent_obj.process_input(user_input)
        
        return jsonify({
            'success': True,
            'response': response,
            'mood': getattr(agent_obj.brain, 'emotional_state', 'curious'),
            'total_interactions': getattr(agent_obj.memory, 'total_interactions', 0),
        })
    except Exception as e:
        logger.error(f"Error in /api/chat: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def stats():
    """Get agent statistics"""
    try:
        agent_obj = get_agent()
        agent_stats = agent_obj.get_stats() if hasattr(agent_obj, 'get_stats') else {}
        return jsonify({
            'success': True,
            'stats': agent_stats,
        })
    except Exception as e:
        logger.error(f"Error in /api/stats: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/memory', methods=['GET'])
def memory():
    """Get agent memory"""
    try:
        agent_obj = get_agent()
        
        memory_data = {}
        if hasattr(agent_obj.memory, 'facts'):
            for topic, facts in agent_obj.memory.facts.items():
                sorted_facts = sorted(facts.items(), key=lambda x: -x[1])[:5]
                memory_data[topic] = [
                    {'fact': fact, 'confidence': round(conf, 2)} 
                    for fact, conf in sorted_facts
                ]
        
        return jsonify({
            'success': True,
            'memory': memory_data,
            'total_topics': len(memory_data),
            'total_facts': sum(len(f) for f in memory_data.values()),
        })
    except Exception as e:
        logger.error(f"Error in /api/memory: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/forget', methods=['POST'])
def forget():
    """Clear all memories"""
    try:
        agent_obj = get_agent()
        if hasattr(agent_obj, 'clear_memory'):
            agent_obj.clear_memory()
        
        return jsonify({
            'success': True,
            'message': 'All memories erased. I am reborn!'
        })
    except Exception as e:
        logger.error(f"Error in /api/forget: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/thoughts', methods=['GET'])
def thoughts():
    """Get autonomous thoughts"""
    try:
        agent_obj = get_agent()
        thought = None
        if hasattr(agent_obj, 'autonomous_thought'):
            thought = agent_obj.autonomous_thought()
        
        return jsonify({
            'success': True,
            'thought': thought or 'I have nothing to contemplate right now...'
        })
    except Exception as e:
        logger.error(f"Error in /api/thoughts: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/ask', methods=['POST'])
def ask():
    """Answer a question"""
    try:
        data = request.json or {}
        question = data.get('question', '').strip()
        
        if not question:
            return jsonify({'error': 'Empty question'}), 400
        
        agent_obj = get_agent()
        
        if hasattr(agent_obj, 'question_answerer'):
            if not agent_obj.question_answerer.is_question(question):
                question += "?"
            
            answer = agent_obj.question_answerer.answer_question(question)
            confidence = agent_obj.question_answerer.get_answer_confidence(
                agent_obj.question_answerer.extract_question_focus(question)
            )
        else:
            answer = "I don't have a question answerer configured yet."
            confidence = 0
        
        return jsonify({
            'success': True,
            'question': question,
            'answer': answer,
            'confidence': round(confidence, 2),
        })
    except Exception as e:
        logger.error(f"Error in /api/ask: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/imagine', methods=['GET'])
def imagine():
    """Generate imaginative thoughts"""
    try:
        agent_obj = get_agent()
        topic = request.args.get('topic', None)
        
        imagination = agent_obj.imagine(topic) if hasattr(agent_obj, 'imagine') else "Imagination unavailable"
        
        return jsonify({
            'success': True,
            'imagination': imagination,
        })
    except Exception as e:
        logger.error(f"Error in /api/imagine: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/graph', methods=['GET'])
def graph_data():
    """Return knowledge graph as nodes + edges"""
    try:
        agent_obj = get_agent()
        
        if not hasattr(agent_obj.brain, 'graph'):
            return jsonify({
                'success': True,
                'nodes': [],
                'edges': [],
                'stats': {'nodes': 0, 'edges': 0, 'inferred': 0}
            })
        
        g = agent_obj.brain.graph
        
        REL_COLOR = {
            'is_a': '#667eea', 'instance_of': '#764ba2',
            'has_property': '#00b894', 'has': '#00cec9',
            'can': '#fdcb6e', 'causes': '#e17055',
            'part_of': '#6c5ce7', 'definition': '#74b9ff',
            'named': '#fd79a8', 'opposite_of': '#d63031',
            'related_to': '#b2bec3',
        }

        nodes = []
        for name, nd in g.nodes.items():
            degree = sum(1 for (s, r, o) in g.edges if s == name or o == name)
            nodes.append({
                'id': name,
                'label': name,
                'type': getattr(nd, 'node_type', 'unknown'),
                'size': max(6, min(24, 6 + degree * 2)),
            })

        edges = []
        for (s, r, o), data in g.edges.items():
            edges.append({
                'source': s,
                'target': o,
                'relation': r,
                'confidence': round(getattr(data, 'confidence', 0.5), 2),
                'inferred': getattr(data, 'inferred', False),
                'color': REL_COLOR.get(r, '#b2bec3'),
            })

        return jsonify({
            'success': True,
            'nodes': nodes,
            'edges': edges,
            'stats': {
                'nodes': len(nodes),
                'edges': len(edges),
                'inferred': sum(1 for e in edges if e['inferred']),
            }
        })
    except Exception as e:
        logger.error(f"Error in /api/graph: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

# ========== ERROR HANDLERS ==========

@app.errorhandler(404)
def not_found(error):
    logger.warning(f"404 Not Found: {request.path}")
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500 Internal Server Error: {error}", exc_info=True)
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    logger.info("Starting Jarvix v2.0 Flask server...")
    logger.info(f"Template directory: {TEMPLATE_DIR}")
    logger.info(f"Data directory: {DATA_DIR}")
    app.run(host='0.0.0.0', port=5000, debug=False)
