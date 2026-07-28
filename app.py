import os
import sys
from flask import Flask, render_template, request, jsonify
from jarvix.agent import Jarvix

app = Flask(__name__)

# Initialize Jarvix Agent
# In production/Docker, save to /app/data/jarvix_v2_memory.json
data_dir = "/app/data" if os.path.exists("/app/data") else "."
data_file = os.path.join(data_dir, "jarvix_v2_memory.json")
agent = Jarvix(data_file=data_file)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """Process user message"""
    data = request.json or {}
    user_input = data.get('message', '').strip()
    
    if not user_input:
        return jsonify({'error': 'Empty message'}), 400
    if len(user_input) > 500:
        return jsonify({'error': 'Message too long (max 500 characters)'}), 400
    
    try:
        response = agent.process_input(user_input)
        return jsonify({
            'success': True,
            'response': response,
            'mood': agent.brain.emotional_state,
            'total_interactions': agent.memory.total_interactions
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats', methods=['GET'])
def stats():
    """Get agent statistics"""
    try:
        return jsonify({
            'success': True,
            'stats': agent.get_stats(),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/memory', methods=['GET'])
def memory():
    """Get agent memory"""
    try:
        memory_data = {}
        for topic, facts in agent.memory.facts.items():
            sorted_facts = sorted(facts.items(), key=lambda x: -x[1]['confidence'] if isinstance(x[1], dict) else -x[1])[:5]
            memory_data[topic] = [
                {
                    'fact': fact, 
                    'confidence': round(info['confidence'] if isinstance(info, dict) else info, 2)
                } 
                for fact, info in sorted_facts
            ]
        return jsonify({
            'success': True,
            'memory': memory_data,
            'total_topics': len(agent.memory.facts),
            'total_facts': sum(len(f) for f in agent.memory.facts.values()),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/forget', methods=['POST'])
def forget():
    """Clear all memories"""
    try:
        agent.clear_memory()
        return jsonify({
            'success': True,
            'message': 'All memories erased. I am reborn!'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/bulk-teach', methods=['POST'])
def bulk_teach():
    """Bulk teach multiple facts"""
    data = request.json or {}
    facts = data.get('facts', [])
    
    if not isinstance(facts, list) or not facts:
        return jsonify({'error': 'Expected list of facts'}), 400
    
    try:
        results = []
        for fact in facts:
            if isinstance(fact, str) and fact.strip():
                response = agent.process_input(fact.strip())
                results.append({
                    'fact': fact,
                    'success': True,
                    'mood': agent.brain.emotional_state
                })
        return jsonify({
            'success': True,
            'taught': len(results),
            'results': results[-10:],
            'stats': agent.get_stats()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/ask', methods=['POST'])
def ask():
    """Answer a question"""
    data = request.json or {}
    question = data.get('question', '').strip()
    
    if not question:
        return jsonify({'error': 'Empty question'}), 400
    
    try:
        answer = agent.brain.answer_question(question)
        return jsonify({
            'success': True,
            'question': question,
            'answer': answer,
            'confidence': agent.get_stats().get('confidence_avg', 0.7)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/thoughts', methods=['GET'])
def thoughts():
    """Get autonomous thoughts"""
    try:
        thought = agent.autonomous_thought()
        return jsonify({
            'success': True,
            'thought': thought
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/dream', methods=['POST'])
def dream():
    """Trigger a background consolidation dream cycle on demand"""
    try:
        report = agent.dream_now()
        return jsonify({
            'success': True,
            'report': report
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/reflect', methods=['POST'])
def reflect():
    """Trigger a self-improvement reflection cycle on demand"""
    try:
        note = agent.reflect()
        return jsonify({
            'success': True,
            'note': note
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/crawl', methods=['POST'])
def crawl():
    """Crawl a URL, learn from it, return structured evaluation"""
    data = request.json or {}
    url = data.get('url', '').strip()
    depth = int(data.get('depth', 1))
    pages = int(data.get('max_pages', 8))
    
    if not url:
        return jsonify({'error': 'url required'}), 400
    if not url.startswith('http'):
        return jsonify({'error': 'url must start with http:// or https://'}), 400
    
    try:
        from jarvix.web_crawler import WebCrawler
        crawler = WebCrawler(agent,
                             max_depth=min(depth, 2),
                             max_pages=min(pages, 15))
        report = crawler.crawl(url)
        eval_ = crawler.build_evaluation(report)
        return jsonify({'success': True, 'evaluation': eval_,
                        'stats': agent.get_stats()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/graph', methods=['GET'])
def graph_data():
    """Return knowledge graph as nodes + edges for 2D visualisation"""
    try:
        g = agent.brain.graph
        
        # Build colour map by relation type
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
                'type': nd.node_type,
                'value': max(5, min(30, 5 + degree * 2)),
                'title': f"Concept: {name}\nConnections: {degree}"
            })
        
        edges = []
        for (s, r, o), data in g.edges.items():
            edges.append({
                'from': s,
                'to': o,
                'label': r,
                'arrows': 'to',
                'color': {'color': REL_COLOR.get(r, '#b2bec3'), 'highlight': '#ff6b6b'},
                'title': f"Relation: {r}\nConfidence: {round(data.confidence, 2)}"
            })
        
        return jsonify({
            'success': True,
            'nodes': nodes,
            'edges': edges,
            'stats': {
                'nodes': len(nodes),
                'edges': len(edges),
                'inferred': sum(1 for e in edges if e.get('inferred', False)),
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'service': 'jarvix-v2',
        'version': '2.0.0'
    })


if __name__ == '__main__':
    # Default port from environment variable
    port = int(os.environ.get('PORT', 5000))
    
    # Check command line arguments for port overrides
    for i, arg in enumerate(sys.argv):
        if arg in ('--port', '-p') and i + 1 < len(sys.argv):
            try:
                port = int(sys.argv[i + 1])
            except ValueError:
                pass
    
    app.run(host='0.0.0.0', port=port, debug=False)